# MoveIt 2 Source Code Modifications

This directory contains patches for the modified MoveIt 2 source code.

## Required Modifications

### moveit_servo_za6_defaults.patch

This patch modifies the default parameters in MoveIt Servo from Panda robot values to ZA6 robot values:

**Changes**:
- `robot_link_command_frame`: `panda_link0` → `tool0`
- `command_out_topic`: `/panda_arm_controller/joint_trajectory` → `/joint_trajectory_controller/joint_trajectory`
- `move_group_name`: `panda_arm` → `manipulator`
- `planning_frame`: `panda_link0` → `world`
- `ee_frame_name`: `panda_link8` → `grasp_link`

**Why**: MoveIt Servo has hardcoded default values for the Franka Panda robot. These defaults are loaded before user-provided parameters, causing the servo node to crash when used with robots that don't have a "panda_arm" move group.

**Note on command_out_topic**: The patch sets the default to `/joint_trajectory_controller/joint_trajectory` which is correct for trajectory-based control. However, when using MoveIt Servo for teleoperation (as in `teleop_hardware.launch.py`), we explicitly override this to `/streaming_controller/commands` in the configuration files (`servo_config.yaml` and inline parameters in the launch file).

**Applying the patch**:
```bash
cd /home/pathpilot/Temp/moveit2
git apply /path/to/patches/moveit_servo_za6_defaults.patch
```

**Build instructions**:
See `REBUILD_SERVO.sh` in the repository root.

**Rebuilding MoveIt2**:
After applying the patch, rebuild MoveIt2:
```bash
# Navigate to MoveIt2 workspace
cd /path/to/moveit2_ws

# Apply the patch first
git apply /path/to/tormach_za_ros2_drivers/patches/moveit_servo_za6_defaults.patch

# Rebuild moveit_servo package
colcon build --packages-select moveit_servo --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Source the install space
source install/setup.bash
```

## Alternative: Modify at Build Time

Instead of applying a patch, the modified `servo_parameters.h` can be used as a template and the defaults can be changed during the Docker build process.

