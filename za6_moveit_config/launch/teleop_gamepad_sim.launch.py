#!/usr/bin/env python3

# Copyright (c) 2023 Tormach, Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the {copyright_holder} nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Declare launch arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "servo_config",
            default_value="servo_config.yaml",
            description="Servo configuration file",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gamepad_config",
            default_value="gamepad_config.yaml", 
            description="Gamepad configuration file",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_rviz",
            default_value="true",
            description="Launch RViz",
        )
    )

    # Initialize Arguments
    servo_config = LaunchConfiguration("servo_config")
    gamepad_config = LaunchConfiguration("gamepad_config")
    use_rviz = LaunchConfiguration("use_rviz")

    # Get package share directory
    pkg_share = FindPackageShare("za6_moveit_config")

    # Include the demo launch (simulation mode)
    demo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_share, "launch", "demo.launch.py"])
        ),
        launch_arguments={
            "use_sim_time": "true",
        }.items(),
    )

    # Joy node for gamepad input
    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        parameters=[
            PathJoinSubstitution([pkg_share, "config", gamepad_config]),
            {"use_sim_time": True},
        ],
        output="screen",
    )

    # Servo node - use parameter file with proper ROS 2 format and override default
    servo_node = Node(
        executable="/tmp/moveit2_za6_ws/install/moveit_servo/lib/moveit_servo/servo_node_main",
        name="servo_node",
        parameters=[
            PathJoinSubstitution([pkg_share, "config", "servo_params.yaml"]),
            {
                "move_group_name": "manipulator",
                "planning_frame": "world",
                "is_primary_planning_scene_monitor": False,
                "ee_frame_name": "grasp_link",
                "robot_link_command_frame": "tool0",
                "halt_all_joints_in_cartesian_mode": False,
                "halt_all_joints_in_joint_mode": False,
                "moveit_servo.command_out_topic": "/joint_trajectory_controller/joint_trajectory",
                "moveit_servo.cartesian_command_in_topic": "/servo_node/delta_twist_cmds",
                "moveit_servo.joint_command_in_topic": "/servo_node/delta_joint_cmds",
                "robot_description_kinematics.manipulator.kinematics_solver": "kdl_kinematics_plugin/KDLKinematicsPlugin",
                "robot_description_kinematics.manipulator.kinematics_solver_search_resolution": 0.005,
                "robot_description_kinematics.manipulator.kinematics_solver_timeout": 0.005,
                "moveit_servo.check_collisions": False,
                "moveit_servo.self_collision_proximity_threshold": 0.1,
                "moveit_servo.scene_collision_proximity_threshold": 0.1,
            }
        ],
        output="screen",
    )

    # Gamepad to servo command converter
    gamepad_converter = Node(
        package="za6_moveit_config",
        executable="gamepad_to_servo.py",
        name="gamepad_to_servo",
        parameters=[
            PathJoinSubstitution([pkg_share, "config", gamepad_config]),
            {"use_sim_time": True},
        ],
        output="screen",
    )

    return LaunchDescription(
        declared_arguments
        + [
            demo_launch,
            joy_node,
            servo_node,
            gamepad_converter,
        ]
    )
