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
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

from launch_ros.parameter_descriptions import ParameterValue

from moveit_configs_utils.launch_utils import (
    add_debuggable_node,
    DeclareBooleanLaunchArg,
)

from moveit_configs_utils import MoveItConfigsBuilder

# Replicate the following:
# from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    builder = MoveItConfigsBuilder("za6", package_name="za6_moveit_config")
    moveit_config = builder.to_moveit_configs()

    ld = LaunchDescription()

    ld.add_action(
        DeclareBooleanLaunchArg(
            "debug",
            default_value=False,
            description="Debug mode; default False",
        )
    )
    ld.add_action(
        DeclareBooleanLaunchArg(
            "allow_trajectory_execution", default_value=True
        )
    )
    ld.add_action(
        DeclareBooleanLaunchArg(
            "publish_monitored_planning_scene", default_value=True
        )
    )
    ld.add_action(
        DeclareLaunchArgument(
            "capabilities",
            default_value="",
            description=(
                "Load non-default MoveGroup capabilities (space separated)"
            ),
        )
    )

    ld.add_action(
        DeclareLaunchArgument(
            "disable_capabilities",
            default_value="",
            description=(
                "Inhibit these default MoveGroup capabilities"
                " (space separated)"
            ),
        )
    )

    ld.add_action(
        DeclareBooleanLaunchArg(
            "monitor_dynamics",
            default_value=False,
            description=(
                "Copy dynamics info from /joint_states"
                " to internal robot monitoring;"
                " default to false, little in move_group needs this"
            ),
        )
    )

    should_publish = LaunchConfiguration("publish_monitored_planning_scene")

    move_group_configuration = {
        "publish_robot_description_semantic": True,
        "allow_trajectory_execution": LaunchConfiguration(
            "allow_trajectory_execution"
        ),
        # Note: Wrapping the following values is necessary so that the parameter
        # value can be the empty string
        "capabilities": ParameterValue(
            LaunchConfiguration("capabilities"), value_type=str
        ),
        "disable_capabilities": ParameterValue(
            LaunchConfiguration("disable_capabilities"), value_type=str
        ),
        # Publish the planning scene of the physical robot so that rviz plugin
        # can know actual robot
        "publish_planning_scene": should_publish,
        "publish_geometry_updates": should_publish,
        "publish_state_updates": should_publish,
        "publish_transforms_updates": should_publish,
        "monitor_dynamics": LaunchConfiguration("monitor_dynamics"),
    }

    move_group_params = [
        moveit_config.to_dict(),
        move_group_configuration,
        {
            "robot_description_kinematics.manipulator.kinematics_solver": "kdl_kinematics_plugin/KDLKinematicsPlugin",
            "robot_description_kinematics.manipulator.kinematics_solver_search_resolution": 0.005,
            "robot_description_kinematics.manipulator.kinematics_solver_timeout": 0.005,
        },
    ]

    add_debuggable_node(
        ld,
        package="moveit_ros_move_group",
        executable="move_group",
        commands_file=str(
            moveit_config.package_path / "launch" / "gdb_settings.gdb"
        ),
        output="screen",
        parameters=move_group_params,
        extra_debug_args=["--debug"],
        # Set the display variable, in case OpenGL code is used internally
        additional_env={"DISPLAY": ":0"},
    )
    return ld
