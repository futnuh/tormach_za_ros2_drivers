#!/usr/bin/env python3

# Launch file to publish static transforms for user-defined frames

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
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import yaml
import os


def load_user_frames(frames_file):
    """Load user frames from YAML file."""
    if not os.path.exists(frames_file):
        return {}
    
    with open(frames_file, 'r') as f:
        data = yaml.safe_load(f)
        # Remove the '---' separator if present
        if isinstance(data, dict):
            return data
        return {}


def quaternion_from_euler(roll, pitch, yaw):
    """Convert Euler angles (roll, pitch, yaw) to quaternion (x, y, z, w)."""
    import math
    
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    qw = cr * cp * cy + sr * sp * sy
    
    return [qx, qy, qz, qw]


def generate_launch_description():
    pkg_share = FindPackageShare("za6_moveit_config")
    default_frames_file = PathJoinSubstitution([pkg_share, "config", "user_frames.yaml"])
    
    # Declare launch argument for frames file
    frames_file_arg = DeclareLaunchArgument(
        "frames_file",
        default_value=default_frames_file,
        description="Path to user frames YAML configuration file",
    )
    
    # Get package path at launch generation time
    import subprocess
    try:
        result = subprocess.run(
            ["ros2", "pkg", "prefix", "za6_moveit_config"],
            capture_output=True,
            text=True,
            check=True
        )
        pkg_path = result.stdout.strip()
        frames_config_path = os.path.join(pkg_path, "share", "za6_moveit_config", "config", "user_frames.yaml")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: try to find from environment or use relative path
        frames_config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "config",
            "user_frames.yaml"
        )
        frames_config_path = os.path.abspath(frames_config_path)
    
    ld = LaunchDescription([frames_file_arg])
    
    # Load frames from file
    frames = load_user_frames(frames_config_path)
    
    # Create static transform publishers for each frame
    node_counter = 0
    for frame_name, frame_data in frames.items():
        if isinstance(frame_data, dict) and "pose" in frame_data:
            pose = frame_data["pose"]
            parent_frame = frame_data.get("parent_frame", "world")
            
            if len(pose) == 6:  # [x, y, z, roll, pitch, yaw]
                x, y, z, roll, pitch, yaw = pose
                qx, qy, qz, qw = quaternion_from_euler(roll, pitch, yaw)
                
                ld.add_action(
                    Node(
                        package="tf2_ros",
                        executable="static_transform_publisher",
                        name=f"user_frame_{frame_name}_{node_counter}",
                        output="log",
                        arguments=[
                            str(x), str(y), str(z),
                            str(qx), str(qy), str(qz), str(qw),
                            parent_frame,
                            frame_name,
                        ],
                    )
                )
                node_counter += 1
    
    return ld

