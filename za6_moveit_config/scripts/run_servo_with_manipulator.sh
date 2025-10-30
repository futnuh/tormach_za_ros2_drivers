#!/bin/bash
# Wrapper script to run servo_node_main with correct move_group_name
# This patches the default 'panda_arm' to 'manipulator' for ZA6

exec ros2 run moveit_servo servo_node_main --ros-args \
  -p move_group_name:=manipulator \
  -p planning_frame:=world \
  -p ee_frame_name:=grasp_link \
  -p robot_link_command_frame:=tool0 \
  "$@"


