#!/bin/bash

# Step 1: Navigate to the build workspace
cd /tmp/moveit2_za6_ws

# Step 2: Create symlink to source
ln -sf /home/pathpilot/Temp/moveit2/moveit_ros src

# Step 3: Set log directory
export COLCON_LOG_DIR=/tmp/moveit2_log

# Step 4: Build moveit_servo with the updated topic
colcon build --packages-select moveit_servo --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

