#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import time
from typing import Dict

import rclcpp
import rclpy
from moveit.task_constructor import core, stages
from moveit_msgs.srv import GetRobotStateFromWarehouse
from moveit_task_constructor_msgs.msg import Solution
from moveit_task_constructor_msgs.action import ExecuteTaskSolution
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from rclpy.action import ActionClient
from builtin_interfaces.msg import Duration


# Named states defined in the MoveIt warehouse
START_STATE_NAME = "WALL_NEUTRAL"
GOAL_STATE_NAME = "DOOR_FACING_NEUTRAL"

# Conservative constant time step (sec) assigned between waypoints
TIME_STEP = 0.5


def _parse_args():
    parser = argparse.ArgumentParser(description="Plan MTC stored state sequence and publish solution")
    parser.add_argument(
        "--auto-execute",
        action="store_true",
        default=False,
        help="Send the ExecuteTaskSolution action automatically (default: manual RViz execution)",
    )
    args, unknown = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + unknown
    return args


# Planning group to use for the ZA6 arm
PLANNING_GROUP = "manipulator"
ROBOT_NAME = "za6"


def _parameterize_solution(solution, time_step: float = 0.2) -> None:
    """Assign monotonically increasing timestamps to each trajectory stored in the solution object."""
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


def fetch_named_states(state_names) -> Dict[str, Dict[str, float]]:
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


def main() -> None:
    args = _parse_args()
    joint_targets = fetch_named_states([START_STATE_NAME, GOAL_STATE_NAME])

    rclcpp.init()
    node = rclcpp.Node("za6_stored_state_sequence")

    task = core.Task()
    task.name = "za6_stored_state_sequence"
    task.loadRobotModel(node)

    task.add(stages.CurrentState("current_state"))

    pipeline = core.PipelinePlanner(node, "ompl")
    pipeline.planner = "RRTConnectkConfigDefault"

    move_to_start = stages.MoveTo(f"Move to {START_STATE_NAME}", pipeline)
    move_to_start.group = PLANNING_GROUP
    move_to_start.setGoal(joint_targets[START_STATE_NAME])
    move_to_start.properties["controller"] = "joint_trajectory_controller"
    task.add(move_to_start)

    move_to_goal = stages.MoveTo(f"Move to {GOAL_STATE_NAME}", pipeline)
    move_to_goal.group = PLANNING_GROUP
    move_to_goal.setGoal(joint_targets[GOAL_STATE_NAME])
    move_to_goal.properties["controller"] = "joint_trajectory_controller"
    task.add(move_to_goal)

    rclpy_node = None
    shutdown_rclpy = False

    try:
        if task.plan():
            for solution in task.solutions:
                _parameterize_solution(solution, time_step=TIME_STEP)
            print(f"Planning succeeded with {len(task.solutions)} solution(s)")

            # Update introspection data so RViz sees the parameterized trajectory
            task.publish(task.solutions[0])
            # Convert to message with explicit timing to satisfy controllers
            solution_msg = task.solutions[0].toMsg(task.introspection())
            if not solution_msg.task_id:
                solution_msg.task_id = task.name
            _parameterize_solution_msg(solution_msg, time_step=TIME_STEP)

            if not rclpy.ok():
                rclpy.init()
                shutdown_rclpy = True

            rclpy_node = rclpy.create_node("mtc_solution_republisher")
            qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                             durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)

            # Debug output of timing information
            for idx, sub_traj in enumerate(solution_msg.sub_trajectory):
                if sub_traj.trajectory.joint_trajectory.points:
                    times = [
                        pt.time_from_start.sec + pt.time_from_start.nanosec * 1e-9
                        for pt in sub_traj.trajectory.joint_trajectory.points
                    ]
                    print(f"SubTrajectory {idx} joint times: {times}")
                if sub_traj.trajectory.multi_dof_joint_trajectory.points:
                    times = [
                        pt.time_from_start.sec + pt.time_from_start.nanosec * 1e-9
                        for pt in sub_traj.trajectory.multi_dof_joint_trajectory.points
                    ]
                    print(f"SubTrajectory {idx} multi-DOF times: {times}")
                if sub_traj.trajectory.joint_trajectory.points and not sub_traj.execution_info.controller_names:
                    sub_traj.execution_info.controller_names.append("joint_trajectory_controller")
                print(f"Stage {sub_traj.info.stage_id} controller info: {sub_traj.execution_info.controller_names}")

            solution_publisher = rclpy_node.create_publisher(Solution, "solution", qos)
            solution_publisher.publish(solution_msg)
            time.sleep(0.1)
            rclpy_node.destroy_publisher(solution_publisher)

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
                print(f"Execution result error_code: {error_code}")
                action_client.destroy()

                rclpy_node.destroy_node()
                rclpy_node = None
                if shutdown_rclpy:
                    rclpy.shutdown()
                    shutdown_rclpy = False
            else:
                print("Solution published. Execute via RViz 'Exec' when ready.")

        if args.auto_execute:
            print("Solution published. Press Enter after execution to exit.")
        else:
            print("Press Enter after manual execution to exit.")
        input()
    finally:
        if rclpy_node is not None:
            rclpy_node.destroy_node()
        if shutdown_rclpy:
            rclpy.shutdown()
        rclcpp.shutdown()


if __name__ == "__main__":
    main()


