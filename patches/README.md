# MoveIt 2 Source Code Modifications

This directory contains patches for the modified MoveIt 2 source code.

## Required Modifications

### moveit_servo_za6_defaults.patch

This patch modifies the default parameters in MoveIt Servo from Panda robot values to ZA6 robot values:

**Changes**:
- `robot_link_command_frame`: `panda_link0` → `tool0`
- `command_out_topic`: `/panda_arm_controller/joint_trajectory` → `/manipulator_controller/joint_trajectory`
- `move_group_name`: `panda_arm` → `manipulator`
- `planning_frame`: `panda_link0` → `world`
- `ee_frame_name`: `panda_link8` → `grasp_link`

**Why**: MoveIt Servo has hardcoded default values for the Franka Panda robot. These defaults are loaded before user-provided parameters, causing the servo node to crash when used with robots that don't have a "panda_arm" move group.

**Applying the patch**:
```bash
cd /home/pathpilot/Temp/moveit2
git apply /path/to/patches/moveit_servo_za6_defaults.patch
```

**Build instructions**:
See `REBUILD_SERVO.sh` in the repository root.

## Alternative: Modify at Build Time

Instead of applying a patch, the modified `servo_parameters.h` can be used as a template and the defaults can be changed during the Docker build process.

