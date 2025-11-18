#!/usr/bin/env python3
"""
Diagnostic script to monitor trajectory velocities and accelerations.

This script subscribes to the joint trajectory controller's action goal topic
and logs the computed velocities/accelerations to help diagnose drive faults
during MoveIt execution.

Usage:
    ros2 run za6_moveit_config diagnose_trajectory.py

Or directly:
    python3 src/tormach_za_ros2_drivers/za6_moveit_config/scripts/diagnose_trajectory.py
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_system_default
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
import numpy as np
from typing import List, Optional


class TrajectoryDiagnostics(Node):
    """Monitor and analyze trajectory velocities/accelerations."""

    def __init__(self):
        super().__init__("trajectory_diagnostics")

        # Read joint limits from parameter server
        self.joint_names = self._get_joint_names()
        self.max_velocities = self._get_max_velocities()
        self.max_accelerations = self._get_max_accelerations()

        # Subscribe to action goals (hidden topic)
        self.action_goal_sub = self.create_subscription(
            FollowJointTrajectory.Goal,
            "/joint_trajectory_controller/follow_joint_trajectory/_action/send_goal",
            self._trajectory_callback,
            qos_profile_system_default,
        )

        self.get_logger().info("Trajectory diagnostics started")
        self.get_logger().info(f"Monitoring {len(self.joint_names)} joints")
        self.get_logger().info("Waiting for trajectory goals...")

    def _get_joint_names(self) -> List[str]:
        """Read joint names from parameter server."""
        try:
            params = self.get_parameters_by_prefix("robot_description_planning.joint_limits")
            # Extract joint names from parameter names like "robot_description_planning.joint_limits.joint_1.max_velocity"
            joint_set = set()
            for param in params:
                parts = param.name.split(".")
                if len(parts) >= 4:
                    joint_set.add(parts[-2])  # e.g., "joint_1"
            return sorted(list(joint_set)) if joint_set else ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]
        except Exception as e:
            self.get_logger().warn(f"Could not read joint names from params: {e}")
            return ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]

    def _get_max_velocities(self) -> dict:
        """Read max velocity limits for each joint."""
        max_vels = {}
        for joint in self.joint_names:
            try:
                param_name = f"robot_description_planning.joint_limits.{joint}.max_velocity"
                max_vel = self.get_parameter(param_name).get_parameter_value().double_value
                max_vels[joint] = max_vel
            except Exception:
                # Use defaults from joint_limits.yaml if not found
                defaults = {
                    "joint_1": 2.0,
                    "joint_2": 3.1,
                    "joint_3": 3.9,
                    "joint_4": 3.0,
                    "joint_5": 3.8,
                    "joint_6": 6.2,
                }
                max_vels[joint] = defaults.get(joint, 2.0)
        return max_vels

    def _get_max_accelerations(self) -> dict:
        """Read max acceleration limits for each joint."""
        max_accels = {}
        for joint in self.joint_names:
            try:
                param_name = f"robot_description_planning.joint_limits.{joint}.max_acceleration"
                max_accel = self.get_parameter(param_name).get_parameter_value().double_value
                max_accels[joint] = max_accel
            except Exception:
                # Use defaults from joint_limits.yaml if not found
                defaults = {
                    "joint_1": 6.0,
                    "joint_2": 10.0,
                    "joint_3": 12.0,
                    "joint_4": 10.0,
                    "joint_5": 12.0,
                    "joint_6": 20.0,
                }
                max_accels[joint] = defaults.get(joint, 6.0)
        return max_accels

    def _trajectory_callback(self, msg: FollowJointTrajectory.Goal):
        """Analyze a trajectory goal message."""
        traj: JointTrajectory = msg.trajectory

        self.get_logger().info("=" * 80)
        self.get_logger().info(f"Received trajectory with {len(traj.points)} points")

        if not traj.points:
            self.get_logger().warn("Empty trajectory!")
            return

        # Map joint names to indices
        joint_to_idx = {name: i for i, name in enumerate(traj.joint_names)}

        # Analyze each joint
        violations = []
        max_velocities_seen = {}
        max_accelerations_seen = {}

        for joint in self.joint_names:
            if joint not in joint_to_idx:
                continue

            idx = joint_to_idx[joint]
            max_vel = self.max_velocities[joint]
            max_accel = self.max_accelerations[joint]

            # Extract positions, velocities, accelerations
            positions = [p.positions[idx] if p.positions else 0.0 for p in traj.points]
            velocities = []
            accelerations = []

            # If velocities are provided, use them; otherwise compute from positions
            if traj.points[0].velocities:
                velocities = [p.velocities[idx] if len(p.velocities) > idx else 0.0 for p in traj.points]
            else:
                # Compute velocities from positions and time
                for i in range(len(traj.points)):
                    if i == 0:
                        velocities.append(0.0)
                    else:
                        dt = self._get_duration(traj.points[i].time_from_start) - self._get_duration(
                            traj.points[i - 1].time_from_start
                        )
                        if dt > 0:
                            vel = abs(positions[i] - positions[i - 1]) / dt
                        else:
                            vel = 0.0
                        velocities.append(vel)

            # If accelerations are provided, use them; otherwise compute from velocities
            if traj.points[0].accelerations:
                accelerations = [p.accelerations[idx] if len(p.accelerations) > idx else 0.0 for p in traj.points]
            else:
                # Compute accelerations from velocities and time
                for i in range(len(traj.points)):
                    if i == 0:
                        accelerations.append(0.0)
                    else:
                        dt = self._get_duration(traj.points[i].time_from_start) - self._get_duration(
                            traj.points[i - 1].time_from_start
                        )
                        if dt > 0:
                            accel = abs(velocities[i] - velocities[i - 1]) / dt
                        else:
                            accel = 0.0
                        accelerations.append(accel)

            # Find maximums
            max_vel_seen = max(abs(v) for v in velocities) if velocities else 0.0
            max_accel_seen = max(abs(a) for a in accelerations) if accelerations else 0.0

            max_velocities_seen[joint] = max_vel_seen
            max_accelerations_seen[joint] = max_accel_seen

            # Check for violations
            vel_violation = max_vel_seen > max_vel
            accel_violation = max_accel_seen > max_accel

            if vel_violation or accel_violation:
                violations.append({
                    "joint": joint,
                    "max_vel_seen": max_vel_seen,
                    "max_vel_limit": max_vel,
                    "vel_violation": vel_violation,
                    "max_accel_seen": max_accel_seen,
                    "max_accel_limit": max_accel,
                    "accel_violation": accel_violation,
                })

            # Log per-joint summary
            status = "⚠️" if (vel_violation or accel_violation) else "✅"
            self.get_logger().info(
                f"{status} {joint:10s}: "
                f"vel={max_vel_seen:6.3f}/{max_vel:4.1f} rad/s "
                f"({max_vel_seen/max_vel*100:5.1f}%), "
                f"accel={max_accel_seen:6.3f}/{max_accel:4.1f} rad/s² "
                f"({max_accel_seen/max_accel*100:5.1f}%)"
            )

        # Summary
        if violations:
            self.get_logger().error("⚠️  LIMIT VIOLATIONS DETECTED:")
            for v in violations:
                if v["vel_violation"]:
                    self.get_logger().error(
                        f"  {v['joint']}: velocity {v['max_vel_seen']:.3f} > limit {v['max_vel_limit']:.1f} rad/s"
                    )
                if v["accel_violation"]:
                    self.get_logger().error(
                        f"  {v['joint']}: acceleration {v['max_accel_seen']:.3f} > limit {v['max_accel_limit']:.1f} rad/s²"
                    )
        else:
            self.get_logger().info("✅ All velocities and accelerations within limits")

        # Trajectory timing summary
        total_time = self._get_duration(traj.points[-1].time_from_start)
        self.get_logger().info(f"Trajectory duration: {total_time:.3f} s")

        # Check for zero or decreasing timestamps
        prev_time = 0.0
        for i, point in enumerate(traj.points):
            current_time = self._get_duration(point.time_from_start)
            if current_time <= prev_time and i > 0:
                self.get_logger().warn(f"⚠️  Non-increasing timestamp at point {i}: {prev_time:.3f} -> {current_time:.3f}")
            prev_time = current_time

        self.get_logger().info("=" * 80)

    @staticmethod
    def _get_duration(time_from_start) -> float:
        """Convert Duration to seconds."""
        return time_from_start.sec + time_from_start.nanosec * 1e-9


def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryDiagnostics()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


