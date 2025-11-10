#!/usr/bin/env python3

# Launch full hardware bringup + MoveIt + teleop (joy → gamepad bridge → Servo)

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch.launch_description_sources import (
    PythonLaunchDescriptionSource,
    AnyLaunchDescriptionSource,
)
from launch_ros.actions import Node
from launch.substitutions import FindExecutable
from launch_ros.substitutions import FindPackageShare
from launch_ros.descriptions import ParameterValue


def generate_launch_description():
    # Args
    declared_arguments = [
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="Use simulation clock if true",
        ),
        DeclareLaunchArgument(
            "use_fake_hardware",
            default_value="false",
            description="Use ros2_control fake hardware",
        ),
        DeclareLaunchArgument(
            "sim_mode",
            default_value="false",
            description="Run HAL in sim mode (ignored when use_fake_hardware:=true)",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="true",
            description="Launch RViz",
        ),
        DeclareLaunchArgument(
            "servo_config",
            default_value="servo_config.yaml",
            description="Servo configuration file in za6_moveit_config/config",
        ),
        DeclareLaunchArgument(
            "gamepad_config",
            default_value="gamepad_config.yaml",
            description="Gamepad configuration file in za6_moveit_config/config",
        ),
        DeclareLaunchArgument(
            "db",
            default_value="false",
            description="Start warehouse database for persistent storage of scenes, states, and motion plans",
        ),
    ]

    use_sim_time = LaunchConfiguration("use_sim_time")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    sim_mode = LaunchConfiguration("sim_mode")
    use_rviz = LaunchConfiguration("use_rviz")
    servo_config = LaunchConfiguration("servo_config")
    gamepad_config = LaunchConfiguration("gamepad_config")
    db = LaunchConfiguration("db")

    # Package shares
    bringup_pkg = FindPackageShare("za6_bringup")
    cfg_pkg = FindPackageShare("za6_moveit_config")

    # Increase CycloneDDS participant limit to avoid "Failed to find a free participant index"
    # Default is 32, but this launch has many nodes
    # Point to config file with MaxAutoParticipantIndex set to 64
    cyclonedds_config_path = PathJoinSubstitution([cfg_pkg, "config", "cyclonedds.xml"])

    set_dds_env = SetEnvironmentVariable(
        name="CYCLONEDDS_URI",
        value=cyclonedds_config_path,
    )

    # 1) Full hardware bringup (HAL + controllers)
    bringup_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            PathJoinSubstitution([bringup_pkg, "launch", "bringup.launch"])  # XML
        ),
        launch_arguments={
            "use_fake_hardware": use_fake_hardware,
            "sim_mode": sim_mode,
            "db": db,
        }.items(),
    )

    # 2) MoveIt move_group
    # Removed here to avoid duplicate move_group when bringup already launches it

    # 3) Joy node (gamepad)
    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        parameters=[
            PathJoinSubstitution([cfg_pkg, "config", gamepad_config]),
            {"use_sim_time": use_sim_time},
        ],
        output="screen",
    )

    # 4) MoveIt Servo (use patched version from /tmp/moveit2_za6_ws)
    # Check if patched version exists, otherwise use package lookup
    patched_servo_path = "/tmp/moveit2_za6_ws/install/moveit_servo/lib/moveit_servo/servo_node_main"
    if os.path.exists(patched_servo_path):
        # Use direct path to patched executable
        servo_node = Node(
            executable=patched_servo_path,
            name="servo_node",
            parameters=[
            # Servo parameters
            PathJoinSubstitution([cfg_pkg, "config", servo_config]),
            # Provide robot_description and SRDF so RobotModelLoader can load kinematics plugins
            {
                "robot_description": ParameterValue(
                    Command([
                        FindExecutable(name="xacro"),
                        " ",
                        PathJoinSubstitution([FindPackageShare("za6_description"), "urdf", "za6.xacro"]),
                    ]),
                    value_type=str
                ),
                "robot_description_semantic": ParameterValue(
                    Command([
                        FindExecutable(name="xacro"),
                        " ",
                        PathJoinSubstitution([cfg_pkg, "config", "za6.srdf.xacro"]),
                    ]),
                    value_type=str
                ),
                # Kinematics parameters for servo node
                "robot_description_kinematics.manipulator.kinematics_solver": "kdl_kinematics_plugin/KDLKinematicsPlugin",
                "robot_description_kinematics.manipulator.kinematics_solver_search_resolution": 0.005,
                "robot_description_kinematics.manipulator.kinematics_solver_timeout": 0.005,
                # Explicitly set servo output topic and type to ensure they override defaults
                "moveit_servo.command_out_topic": "/streaming_controller/commands",
                "moveit_servo.command_out_type": "std_msgs/Float64MultiArray",
                # Required for std_msgs/Float64MultiArray: exactly one of positions or velocities must be true
                "moveit_servo.publish_joint_positions": True,
                "moveit_servo.publish_joint_velocities": False,
                "moveit_servo.publish_joint_accelerations": False,
            },
            {"use_sim_time": use_sim_time},
        ],
        output="screen",
        )
    else:
        # Fallback to package lookup (if patched version not available)
        servo_node = Node(
            package="moveit_servo",
            executable="servo_node_main",
            name="servo_node",
            parameters=[
                # Servo parameters
                PathJoinSubstitution([cfg_pkg, "config", servo_config]),
                # Provide robot_description and SRDF so RobotModelLoader can load kinematics plugins
                {
                    "robot_description": ParameterValue(
                        Command([
                            FindExecutable(name="xacro"),
                            " ",
                            PathJoinSubstitution([FindPackageShare("za6_description"), "urdf", "za6.xacro"]),
                        ]),
                        value_type=str
                    ),
                    "robot_description_semantic": ParameterValue(
                        Command([
                            FindExecutable(name="xacro"),
                            " ",
                            PathJoinSubstitution([cfg_pkg, "config", "za6.srdf.xacro"]),
                        ]),
                        value_type=str
                    ),
                    # Kinematics parameters for servo node
                    "robot_description_kinematics.manipulator.kinematics_solver": "kdl_kinematics_plugin/KDLKinematicsPlugin",
                    "robot_description_kinematics.manipulator.kinematics_solver_search_resolution": 0.005,
                    "robot_description_kinematics.manipulator.kinematics_solver_timeout": 0.005,
                    # Explicitly set servo output topic and type to ensure they override defaults
                    "moveit_servo.command_out_topic": "/streaming_controller/commands",
                    "moveit_servo.command_out_type": "std_msgs/Float64MultiArray",
                    # Required for std_msgs/Float64MultiArray: exactly one of positions or velocities must be true
                    "moveit_servo.publish_joint_positions": True,
                    "moveit_servo.publish_joint_velocities": False,
                    "moveit_servo.publish_joint_accelerations": False,
                },
                {"use_sim_time": use_sim_time},
            ],
            output="screen",
        )

    # 5) Gamepad → Servo bridge
    gamepad_bridge = Node(
        package="za6_moveit_config",
        executable="gamepad_to_servo.py",
        name="gamepad_to_servo",
        parameters=[
            PathJoinSubstitution([cfg_pkg, "config", gamepad_config]),
            {"use_sim_time": use_sim_time},
        ],
        output="screen",
    )

    # 6) RViz (optional)
    moveit_rviz = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(PathJoinSubstitution([cfg_pkg, "launch", "moveit_rviz.launch.py"])),
        condition=IfCondition(use_rviz),
        launch_arguments={
            "rviz_config": PathJoinSubstitution([cfg_pkg, "config", "moveit.rviz"]),
        }.items(),
    )

    # 7) Warehouse DB (optional)
    warehouse_db_launch = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(PathJoinSubstitution([cfg_pkg, "launch", "warehouse_db.launch.py"])),
        condition=IfCondition(db),
    )

    return LaunchDescription(declared_arguments + [
        set_dds_env,
        bringup_launch,
        joy_node,
        servo_node,
        gamepad_bridge,
        moveit_rviz,
        warehouse_db_launch,
    ])


