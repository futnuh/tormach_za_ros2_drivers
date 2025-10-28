# MoveIt Servo Integration for ZA6 Robot

## Overview

This document describes how to integrate MoveIt Servo for gamepad teleoperation with the ZA6 robot. The integration includes both software configuration and hardware-specific modifications to the MoveIt 2 source code.

## Problem

MoveIt Servo contains hardcoded default values for the Franka Panda robot (`panda_arm`, `panda_link0`, etc.) that don't match the ZA6 robot configuration. These hardcoded defaults are loaded in the `ServoNode` constructor *before* any user-provided parameters from YAML files can be applied, causing the servo node to crash with the error:

```
Group 'panda_arm' not found in model 'za6'
```

## Solution

To work around this limitation, we modified the MoveIt Servo source code to change the hardcoded defaults to match the ZA6 robot. The modified defaults are:

| Parameter | Original (Panda) | Modified (ZA6) |
|-----------|------------------|-----------------|
| `move_group_name` | `panda_arm` | `manipulator` |
| `planning_frame` | `panda_link0` | `world` |
| `ee_frame_name` | `panda_link8` | `grasp_link` |
| `robot_link_command_frame` | `panda_link0` | `tool0` |
| `command_out_topic` | `/panda_arm_controller/joint_trajectory` | `/manipulator_controller/joint_trajectory` |

## File Locations

The modified file is located at:
- `/tmp/moveit2_za6_ws/src/moveit_ros/moveit_servo/include/moveit_servo/servo_parameters.h`
- Modified lines: 67, 75, 85, 86, 87

## Build Process

The modified MoveIt Servo is built in a separate workspace (`/tmp/moveit2_za6_ws`) to avoid permission issues with the main workspace. The build process uses a symlink approach:

```bash
cd /tmp/moveit2_za6_ws
ln -sf /home/pathpilot/Temp/moveit2/moveit_ros src
colcon build --packages-select moveit_servo
```

## Integration into Docker

To make this work in a reproducible Docker build, you would need to:

1. **Option A: Patch during Docker build**
   - Add a `Dockerfile` instruction to clone MoveIt 2 source code
   - Apply a patch that changes the hardcoded values
   - Build MoveIt Servo from source in the Docker image

2. **Option B: Use pre-built modified package**
   - Build MoveIt Servo outside Docker with the modifications
   - Copy the built package into the Docker image
   - Install it in the container

3. **Option C: Submit upstream patch**
   - Submit a PR to MoveIt 2 to make these parameters truly configurable
   - Wait for upstream adoption
   - Use the unmodified upstream version once merged

## Current Status

✅ **Working**: The modified MoveIt Servo is built and tested
✅ **Teleoperation**: Gamepad control works with the ZA6 robot
⚠️ **Note**: The modification is a workaround and not a permanent solution

## Usage

After building the modified MoveIt Servo:

```bash
# Source the modified MoveIt Servo
source /tmp/moveit2_za6_ws/install/setup.bash

# Launch teleoperation
ros2 launch za6_moveit_config teleop_gamepad_sim.launch.py

# In another terminal, unpause the servo:
ros2 service call /servo_node/unpause_servo std_srvs/srv/Trigger
```

## Gamepad Controls

- **Button A (Xbox, 0 in D-Input)**: Enable servo
- **Button B (Xbox, 1 in D-Input)**: Disable servo  
- **Left Bumper (4)**: Cartesian mode
- **Right Bumper (5)**: Joint mode
- **Left Stick**: Translation (Cartesian) or joint velocities (Joint)
- **Right Stick**: Rotation (Cartesian)

## Configuration Files

- `za6_moveit_config/config/servo_config.yaml`: Real hardware configuration
- `za6_moveit_config/config/servo_config_sim.yaml`: Simulation configuration (slower speeds)
- `za6_moveit_config/config/gamepad_config.yaml`: Gamepad button/axis mappings

## Related Files

- `za6_moveit_config/scripts/gamepad_to_servo.py`: Converts gamepad input to servo commands
- `za6_moveit_config/launch/teleop_gamepad_sim.launch.py`: Launch file for teleoperation
- `BUILD_MOVEIT_TMP.sh`: Build script for modified MoveIt Servo

## Next Steps

For a production-ready PR:

1. Create a patch file for MoveIt 2 that makes the hardcoded parameters truly configurable
2. Update the Dockerfile to apply this patch during build
3. Add documentation on how to build and install the modified MoveIt Servo
4. Consider submitting an upstream PR to MoveIt 2 to make these parameters properly configurable

