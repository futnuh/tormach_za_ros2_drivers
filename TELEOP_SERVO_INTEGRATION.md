# Work Summary: MoveIt Servo Teleoperation Integration

## Overview
Successfully integrated MoveIt Servo for gamepad-based teleoperation with the ZA6 robot hardware. All critical issues were resolved and the system is now fully functional.

## Objective
Enable real-time gamepad-based teleoperation for the ZA6 robot using MoveIt Servo, integrating with hardware via the streaming controller.

## Issues Resolved

1. ✅ **Servo node crashing at startup** - Parameter validation error when using `std_msgs/Float64MultiArray`
2. ✅ **Servo not publishing commands** - Incorrect output topic configuration
3. ✅ **CycloneDDS participant limit exceeded** - Too many ROS nodes in launch
4. ✅ **Deprecated controller manager API** - Using old `start_controllers`/`stop_controllers` API
5. ✅ **YAML parameter structure issues** - Missing `ros__parameters` wrapper

---

## Files Modified

### 1. `za6_moveit_config/config/kinematics.yaml`
**Change:** Added `ros__parameters:` wrapper for proper ROS2 parameter structure

**Before:**
```yaml
robot_description_kinematics:
  manipulator:
    kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin
```

**After:**
```yaml
robot_description_kinematics:
  ros__parameters:
    manipulator:
      kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin
```

### 2. `za6_moveit_config/config/servo_config.yaml`
**Changes:**
- Restructured entire file under `moveit_servo.ros__parameters:` namespace
- Fixed input topics to match `gamepad_to_servo.py`:
  - `cartesian_command_in_topic`: `/servo_node/delta_twist_cmds` (was `/servo_cmd/pose`)
  - `joint_command_in_topic`: `/servo_node/delta_joint_cmds` (was `/servo_cmd/joint`)
  - `status_topic`: `/servo_node/status` (was `/servo/status`)
- **Critical fix:** Changed output topic from `/joint_trajectory_controller/joint_trajectory` to `/streaming_controller/commands`
- Kept `command_out_type: std_msgs/Float64MultiArray` with `publish_joint_positions: true`

### 3. `za6_moveit_config/scripts/gamepad_to_servo.py`
**Changes:**
- Updated to ROS2 Humble controller manager API:
  - Replaced deprecated `start_controllers`/`stop_controllers` with `activate_controllers`/`deactivate_controllers`
- Added proper async callback handling for controller switch responses
- Changed switch mode to `BEST_EFFORT` when enabling servo (to handle pre-activated streaming controller)
- Improved error handling and logging for async service calls

**Key updates:**
- `_switch_controllers()`: Renamed parameters (`start`→`activate`, `stop`→`deactivate`), added async callback
- Added `_switch_controller_callback()` method for logging switch results
- Updated all calls to use new API with clearer parameter names

---

## Files Created

### 1. `za6_moveit_config/launch/teleop_hardware.launch.py`
**Purpose:** New comprehensive launch file for full hardware teleoperation

**Features:**
- Hardware bringup integration (HAL + controllers via `za6_bringup`)
- MoveIt Servo node with proper kinematics and parameter configuration
- Joy node for gamepad input
- Gamepad-to-Servo bridge node
- CycloneDDS configuration for increased participant limit
- Inline kinematics parameters for servo node
- Explicit servo output configuration to override defaults:
  - `command_out_topic`: `/streaming_controller/commands`
  - `command_out_type`: `std_msgs/Float64MultiArray`
  - `publish_joint_positions`: `True`
  - `publish_joint_velocities`: `False`
  - `publish_joint_accelerations`: `False`
- Proper `ParameterValue` wrapping for robot_description strings (prevents YAML parsing errors)

### 2. `za6_moveit_config/config/cyclonedds.xml`
**Purpose:** CycloneDDS configuration file to increase participant limit

**Configuration:**
- Increased `MaxAutoParticipantIndex` from default 32 to 64
- Configured for localhost loopback interface
- Disabled multicast for single-machine deployment

**Reason:** The teleop launch file has many ROS nodes (>32), which exceeds the default CycloneDDS participant limit.

### 3. `za6_moveit_config/config/servo_kinematics.yaml` (untracked)
- Created initially but ultimately not used (kinematics moved inline in launch file)
- Contains same kinematics configuration for reference

---

## Technical Details

### MoveIt2 Source Code Modifications

**Important:** MoveIt2 was rebuilt from patched source code for this teleoperation integration.

**Why a patch was required:**
MoveIt Servo contains hardcoded default values for the Franka Panda robot (`panda_arm`, `panda_link0`, etc.) in `servo_parameters.h`. These defaults are applied during `ServoNode` construction *before* user-provided parameters can override them, causing the servo node to crash when used with robots that don't have a "panda_arm" move group.

**Patch location:**
- Patch file: `patches/moveit_servo_za6_defaults.patch` (in this repository)
- Patched source code: `/home/pathpilot/Temp/moveit2/` (separate git repository, not in this repo)
- Build workspace: `/tmp/moveit2_za6_ws/` (symlinks to patched source)
- Rebuild script: `REBUILD_SERVO.sh` (in this repository root)

**Patch modifications:**
The patch changes MoveIt Servo defaults from Panda values to ZA6 values:
- `robot_link_command_frame`: `panda_link0` → `tool0`
- `command_out_topic`: `/panda_arm_controller/joint_trajectory` → `/joint_trajectory_controller/joint_trajectory`
- `move_group_name`: `panda_arm` → `manipulator`
- `planning_frame`: `panda_link0` → `world`
- `ee_frame_name`: `panda_link8` → `grasp_link`

**Implementation details:**
- **Not using ComposableNode**: The implementation uses the standalone `servo_node_main` executable, not the composable node interface
- While `ServoNode` supports composable node usage (it has `RCLCPP_COMPONENTS_REGISTER_NODE`), the launch file uses `executable="servo_node_main"` which is the traditional ROS2 node approach
- The patched source supports both approaches, but the standalone executable is what's currently used

**Rebuilding MoveIt2:**
After applying the patch, MoveIt2 must be rebuilt:
```bash
# Apply the patch
cd /home/pathpilot/Temp/moveit2
git apply /path/to/tormach_za_ros2_drivers/patches/moveit_servo_za6_defaults.patch

# Rebuild moveit_servo package
cd /tmp/moveit2_za6_ws
ln -sf /home/pathpilot/Temp/moveit2/moveit_ros src
colcon build --packages-select moveit_servo --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

**Note:** Even with the patched defaults, configuration files (`servo_config.yaml` and inline parameters in `teleop_hardware.launch.py`) override `command_out_topic` to `/streaming_controller/commands` for servo teleoperation, while the patch default of `/joint_trajectory_controller/joint_trajectory` remains correct for trajectory-based control.

For detailed patch information, see `patches/README.md`.

### Parameter Structure Fixes
1. **Robot Description**: Wrapped `Command()` output with `ParameterValue(..., value_type=str)` to explicitly tell launch system these are strings (URDF/XML), not YAML to parse
2. **Servo Parameters**: Added explicit inline parameters in launch file to ensure proper application:
   - **Critical:** For `std_msgs/Float64MultiArray`, MoveIt Servo requires exactly ONE of `publish_joint_positions` or `publish_joint_velocities` to be `True`, not both, not neither.

### Controller Switching Improvements
- Updated to ROS2 Humble API (`activate_controllers`/`deactivate_controllers` instead of deprecated `start_controllers`/`stop_controllers`)
- Added proper async callback handling for switch operations
- Improved error handling for edge cases (e.g., controller already active)

### DDS Configuration
- Increased CycloneDDS participant limit from 32 to 64 via `CYCLONEDDS_URI` environment variable
- Prevents "Failed to find a free participant index" errors with many nodes

---

## Current Status

✅ **Servo node starts successfully** with proper parameter validation  
✅ **Servo publishes joint positions** to `/streaming_controller/commands`  
✅ **Gamepad input properly converted** to servo commands  
✅ **Controller switching works** between `streaming_controller` (teleop) and `joint_trajectory_controller` (planning)  
✅ **Hardware initialization completes** successfully  
✅ **Teleoperation functional**: Button 1 enables servo, joysticks control robot

### Usage
```bash
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false \
  sim_mode:=false \
  use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml \
  gamepad_config:=gamepad_config.yaml
```

**Controls:**
- **Button 7 (START)**: Toggle teleoperation (enter/exit)
  - Press to enter: Switches to streaming controller, unpauses and starts servo
  - Press again to exit: Pauses servo, switches back to joint_trajectory_controller
- **Button 6 (SELECT)**: Toggle between cartesian/joint mode
- **Joysticks**: Control robot motion
  - Left stick: Joint 1 (X), Joint 2 (Y)
  - Right stick: Joint 3 (X), Joint 5 (Y) - note: joint 4 and 5 controls are swapped
  - Triggers/DPad: Joint 4 and Joint 6 (Joint 6 has 2x speed multiplier)

---

## Summary

All issues have been resolved and the system is fully functional. Key improvements include proper parameter structure, explicit parameter setting, DDS configuration, and updated controller manager API usage. The robot can now be controlled in real-time via gamepad with MoveIt Servo.
