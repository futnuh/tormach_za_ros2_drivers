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
- **Button 1 (A)**: Enable servo/teleoperation mode
- **Button 0 (X)**: Disable servo mode
- **Bumper 4**: Cartesian mode
- **Bumper 5**: Joint mode
- **Joysticks**: Control robot motion

---

## Summary

All issues have been resolved and the system is fully functional. Key improvements include proper parameter structure, explicit parameter setting, DDS configuration, and updated controller manager API usage. The robot can now be controlled in real-time via gamepad with MoveIt Servo.
