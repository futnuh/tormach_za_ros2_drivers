#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prototype MoveIt Task Constructor pipeline with gripper I/O toggles.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
import subprocess
from typing import Dict, List

import rclcpp
import rclpy
from builtin_interfaces.msg import Duration
from ament_index_python.packages import get_package_share_directory
from moveit.task_constructor import core, stages
from moveit_msgs.srv import GetRobotStateFromWarehouse
from moveit_task_constructor_msgs.action import ExecuteTaskSolution
from moveit_task_constructor_msgs.msg import Solution, TrajectoryExecutionInfo
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy

# Ensure helper modules are importable when installed under lib/za6_moveit_config
CURRENT_DIR = Path(__file__).resolve().parent
IO_DIR = CURRENT_DIR.parent / "io"
if str(IO_DIR) not in sys.path:
    sys.path.append(str(IO_DIR))

from gripper_io import GripperController  # type: ignore  # pylint: disable=wrong-import-position
import yaml


START_STATE_NAME = "WALL_NEUTRAL"
PREGRASP_STATE_NAME = "DOOR_FACING_NEUTRAL"
RETREAT_STATE_NAME = "WALL_NEUTRAL"

PLANNING_GROUP = "manipulator"
ROBOT_NAME = "za6"
TIME_STEP = 0.5


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ZA6 MTC pipeline experiment with gripper toggles")
    parser.add_argument(
        "--auto-execute",
        action="store_true",
        default=False,
        help="Send the ExecuteTaskSolution action automatically (default: manual RViz execution)",
    )
    parser.add_argument(
        "--wait-for-feedback",
        action="store_true",
        default=False,
        help="Wait for HAL feedback before proceeding past gripper stages",
    )
    parser.add_argument(
        "--feedback-timeout",
        type=float,
        default=1.0,
        help="Seconds to wait for feedback when --wait-for-feedback is enabled",
    )
    args, unknown = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + unknown
    return args


def _parameterize_solution(solution, time_step: float = 0.2) -> None:
    trajectory = getattr(solution, "trajectory", None)
    if trajectory:
        waypoint_count = trajectory.getWayPointCount()
        if waypoint_count > 1:
            for idx in range(1, waypoint_count):
                trajectory.setWayPointDurationFromPrevious(idx, time_step)

    for attr in ("solutions", "subsolutions"):
        if hasattr(solution, attr):
            nested = getattr(solution, attr)
            if callable(nested):
                try:
                    nested = nested()
                except TypeError:
                    continue
            try:
                for sub in nested:
                    _parameterize_solution(sub, time_step)
            except TypeError:
                pass


def _parameterize_solution_msg(solution_msg: Solution, time_step: float = 0.2) -> None:
    for sub_traj in solution_msg.sub_trajectory:
        joint_traj = sub_traj.trajectory.joint_trajectory
        if joint_traj.points:
            current = 0.0
            for point in joint_traj.points:
                point.time_from_start = Duration()
                point.time_from_start.sec = int(current)
                point.time_from_start.nanosec = int((current - int(current)) * 1e9)
                current += time_step

        multi_dof = sub_traj.trajectory.multi_dof_joint_trajectory
        if multi_dof.points:
            current = 0.0
            for point in multi_dof.points:
                point.time_from_start = Duration()
                point.time_from_start.sec = int(current)
                point.time_from_start.nanosec = int((current - int(current)) * 1e9)
                current += time_step


def fetch_named_states(state_names: List[str]) -> Dict[str, Dict[str, float]]:
    initialized = False
    if not rclpy.ok():
        rclpy.init()
        initialized = True

    try:
        node = rclpy.create_node("warehouse_state_fetcher")
    except RuntimeError as exc:
        raise RuntimeError("Failed to create ROS node. Check DDS participant limits.") from exc
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    client = node.create_client(GetRobotStateFromWarehouse, "/get_robot_state")
    if not client.wait_for_service(timeout_sec=5.0):
        executor.remove_node(node)
        node.destroy_node()
        if initialized:
            rclpy.shutdown()
        raise RuntimeError("Warehouse service '/get_robot_state' unavailable")

    results: Dict[str, Dict[str, float]] = {}
    for name in state_names:
        request = GetRobotStateFromWarehouse.Request()
        request.name = name
        request.robot = ROBOT_NAME

        future = client.call_async(request)
        executor.spin_until_future_complete(future, timeout_sec=10.0)
        response = future.result()
        if response is None:
            executor.remove_node(node)
            node.destroy_node()
            if initialized:
                rclpy.shutdown()
            raise RuntimeError(f"Failed to retrieve stored state '{name}'")

        joint_state = response.state.joint_state
        if not joint_state.name:
            executor.remove_node(node)
            node.destroy_node()
            if initialized:
                rclpy.shutdown()
            raise RuntimeError(f"Stored state '{name}' contains no joint data")

        results[name] = dict(zip(joint_state.name, joint_state.position))

    executor.remove_node(node)
    node.destroy_node()
    if initialized:
        rclpy.shutdown()

    return results


def _declare_parameter(node, name: str, value):
    try:
        node.declare_parameter(name, value)
    except Exception:
        # Parameter already declared; that's fine
        pass
    # Ensure the parameter actually has the desired value
    try:
        node.set_parameter(rclcpp.Parameter(name, value))
    except Exception:
        pass


def _declare_parameter_tree(node, prefix: str, data):
    full_name = prefix if prefix else ""
    if isinstance(data, dict):
        for sub_key, sub_value in data.items():
            new_prefix = f"{full_name}.{sub_key}" if full_name else sub_key
            _declare_parameter_tree(node, new_prefix, sub_value)
    else:
        _declare_parameter(node, full_name, data)


def configure_ompl_pipeline(node) -> None:
    """Declare OMPL and kinematics parameters on the given rclcpp node."""
    share_dir = Path(get_package_share_directory("za6_moveit_config"))
    ompl_yaml = share_dir / "config" / "ompl_planning.yaml"
    with ompl_yaml.open("r") as stream:
        ompl_params = yaml.safe_load(stream)

    _declare_parameter_tree(node, "ompl", ompl_params)

    kin_yaml = share_dir / "config" / "kinematics.yaml"
    with kin_yaml.open("r") as stream:
        kin_params = yaml.safe_load(stream)

    _declare_parameter_tree(node, "robot_description_kinematics", kin_params)

    declared = {
        "planning_pipelines": ["ompl"],
        "ompl.planning_plugin": "ompl_interface/OMPLPlanner",
        "planning_plugin": "ompl_interface/OMPLPlanner",
        "default_planning_pipeline": "ompl",
        "move_group.planning_plugin": "ompl_interface/OMPLPlanner",
        "move_group.planning_pipelines": ["ompl"],
        "move_group.default_planning_pipeline": "ompl",
    }
    for key, value in declared.items():
        _declare_parameter(node, key, value)

    print("[INFO] Declared MTC planning parameters:")
    for key, value in declared.items():
        print(f"  {key}: {value}")

def _print_move_group_planning_params() -> None:
    """Log MoveGroup planner-related parameters via ROS 2 CLI."""
    commands = [
        ["ros2", "param", "get", "/move_group", "planning_plugin"],
        ["ros2", "param", "get", "/move_group", "planning_pipelines"],
        ["ros2", "param", "get", "/move_group", "default_planning_pipeline"],
    ]
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            print("[WARN] 'ros2' CLI not found; skipping move_group parameter checks")
            break

        if result.returncode == 0:
            output = result.stdout.strip()
        else:
            output = result.stderr.strip()

        print(f"[INFO] {' '.join(cmd)} -> {output}")
def create_toggle_stage(
    name: str,
    gripper: GripperController,
    open_state: bool,
    wait_for_feedback: bool,
    feedback_timeout: float,
) -> core.Stage:
    stage = stages.ModifyPlanningScene(name)
    state_str = "open" if open_state else "close"
    execution_info = TrajectoryExecutionInfo()
    execution_info.controller_names = [f"io_toggle_gripper:{state_str}"]
    stage.setTrajectoryExecutionInfo(execution_info)
    return stage


def _apply_gripper_command(
    gripper: GripperController,
    open_state: bool,
    wait_for_feedback: bool,
    feedback_timeout: float,
) -> bool:
    success = (
        gripper.command_open(wait_for_feedback, feedback_timeout)
        if open_state
        else gripper.command_close(wait_for_feedback, feedback_timeout)
    )
    if not success:
        print(
            f"[WARN] Gripper command timed out (open={open_state}, timeout={feedback_timeout:.2f}s)",
            flush=True,
        )

    return success


def build_task(
    mtc_node,
    joint_targets: Dict[str, Dict[str, float]],
    gripper_controller: GripperController,
    wait_for_feedback: bool,
    feedback_timeout: float,
):
    task = core.Task()
    task.name = "za6_mtc_pipeline_experiment"
    task.loadRobotModel(mtc_node)
    task.add(stages.CurrentState("current_state"))

    pipeline = core.PipelinePlanner(mtc_node, "move_group")
    pipeline.planning_plugin = "ompl_interface/OMPLPlanner"

    toggle_open = create_toggle_stage(
        "Toggle gripper open",
        gripper_controller,
        open_state=True,
        wait_for_feedback=wait_for_feedback,
        feedback_timeout=feedback_timeout,
    )
    move_to_start = stages.MoveTo(f"Move to {START_STATE_NAME}", pipeline)
    move_to_start.group = PLANNING_GROUP
    move_to_start.setGoal(joint_targets[START_STATE_NAME])
    move_to_start.properties["controller"] = "joint_trajectory_controller"
    task.add(move_to_start)
    task.add(toggle_open)

    toggle_close = create_toggle_stage(
        "Toggle gripper close",
        gripper_controller,
        open_state=False,
        wait_for_feedback=wait_for_feedback,
        feedback_timeout=feedback_timeout,
    )
    move_to_pregrasp = stages.MoveTo(f"Move to {PREGRASP_STATE_NAME}", pipeline)
    move_to_pregrasp.group = PLANNING_GROUP
    move_to_pregrasp.setGoal(joint_targets[PREGRASP_STATE_NAME])
    move_to_pregrasp.properties["controller"] = "joint_trajectory_controller"
    task.add(move_to_pregrasp)
    task.add(toggle_close)

    move_to_retreat = stages.MoveTo(f"Retreat to {RETREAT_STATE_NAME}", pipeline)
    move_to_retreat.group = PLANNING_GROUP
    move_to_retreat.setGoal(joint_targets[RETREAT_STATE_NAME])
    move_to_retreat.properties["controller"] = "joint_trajectory_controller"
    task.add(move_to_retreat)

    return task


def main() -> None:
    args = _parse_args()
    joint_targets = fetch_named_states([START_STATE_NAME, PREGRASP_STATE_NAME, RETREAT_STATE_NAME])

    rclcpp.init()
    mtc_node = rclcpp.Node("za6_mtc_pipeline_experiment")
    configure_ompl_pipeline(mtc_node)
    _print_move_group_planning_params()

    if not rclpy.ok():
        rclpy.init()

    rclpy_node = rclpy.create_node("za6_gripper_io_helper")
    gripper_controller = GripperController(rclpy_node)

    task = build_task(
        mtc_node,
        joint_targets,
        gripper_controller,
        wait_for_feedback=args.wait_for_feedback,
        feedback_timeout=args.feedback_timeout,
    )

    rclpy_node_logger = rclpy_node.get_logger()

    solution_msg = None
    try:
        if task.plan():
            for solution in task.solutions:
                _parameterize_solution(solution, time_step=TIME_STEP)
            print(f"Planning succeeded with {len(task.solutions)} solution(s)")

            task.publish(task.solutions[0])
            solution_msg = task.solutions[0].toMsg(task.introspection())
            if not solution_msg.task_id:
                solution_msg.task_id = task.name
            _parameterize_solution_msg(solution_msg, time_step=TIME_STEP)

            qos = QoSProfile(
                depth=1,
                reliability=QoSReliabilityPolicy.RELIABLE,
                durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            )
            solution_pub = rclpy_node.create_publisher(Solution, "solution", qos)
            solution_pub.publish(solution_msg)
            time.sleep(0.1)
            rclpy_node.destroy_publisher(solution_pub)

            if args.auto_execute:
                action_client = ActionClient(rclpy_node, ExecuteTaskSolution, "execute_task_solution")
                if not action_client.wait_for_server(timeout_sec=5.0):
                    raise RuntimeError("execute_task_solution action server not available")

                goal_msg = ExecuteTaskSolution.Goal()
                goal_msg.solution = solution_msg

                send_goal_future = action_client.send_goal_async(goal_msg)
                rclpy.spin_until_future_complete(rclpy_node, send_goal_future)
                goal_handle = send_goal_future.result()
                if not goal_handle or not goal_handle.accepted:
                    raise RuntimeError("execute_task_solution goal rejected")

                result_future = goal_handle.get_result_async()
                rclpy.spin_until_future_complete(rclpy_node, result_future)
                result = result_future.result()
                error_code = getattr(result.result.error_code, "val", None)
                rclpy_node_logger.info(f"Execution result error_code: {error_code}")
                action_client.destroy()

        else:
            print("Solution published. Execute via RViz 'Exec' when ready.")

        prompt = "Press Enter after execution to exit." if args.auto_execute else "Press Enter to exit."
        input(prompt)
    finally:
        gripper_controller.destroy()
        rclpy_node.destroy_node()
        rclcpp.shutdown()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()


