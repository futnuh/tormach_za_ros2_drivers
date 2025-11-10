# Analysis: panda_arm Hardcode in MoveIt Servo

> **Note**: This is a historical analysis document. The issue described has been resolved. See `TELEOP_SERVO_INTEGRATION.md` and `patches/README.md` for the current solution.

## Problem Summary
MoveIt Servo hardcodes `"panda_arm"` as the default value for the `move_group_name` parameter. This prevents the ZA6 robot from using MoveIt Servo because the ZA6 uses `"manipulator"` as its move group name.

## Root Cause Location

### File: `servo_parameters.h` (Line 85)
```cpp
std::string move_group_name{ "panda_arm" };
```
This is the hardcoded default value in the `ServoParameters` struct.

### File: `servo_parameters.cpp` (Line 188-190)
```cpp
node_parameters->declare_parameter(
    ns + ".move_group_name", ParameterValue{ parameters.move_group_name },
    ParameterDescriptorBuilder{}.type(PARAMETER_STRING).description("Often 'manipulator' or 'arm'"));
```
This declares the parameter using the default value from the struct.

### File: `servo_calcs.cpp` (Line 89)
```cpp
joint_model_group_ = current_state_->getJointModelGroup(parameters_->move_group_name);
if (joint_model_group_ == nullptr)
{
  RCLCPP_ERROR_STREAM(LOGGER, "Invalid move group name: `" << parameters_->move_group_name << "`");
  throw std::runtime_error("Invalid move group name");
}
```
This is where the error occurs - it tries to get the joint model group using the parameter value, which is still "panda_arm" at this point.

## Why Parameter Loading Fails

### Execution Flow
1. `servo_node_main.cpp` (line 48): Creates `ServoNode` with `NodeOptions`
2. `servo_node.cpp` (line 48): `ServoNode` constructor creates the node
3. `servo_node.cpp` (line 81): Calls `makeServoParameters(node_)`
4. `servo_parameters.cpp` (line 463): Calls `declare(ns, node_parameters)` 
5. `declare()` (line 97): Creates empty `ServoParameters{}` which uses struct defaults ("panda_arm")
6. `declare()` (line 188-190): Declares parameter with that default value
7. Back to `servo_node.cpp` (line 108): Creates `Servo` with these parameters
8. `servo.cpp` (line 55): Creates `ServoCalcs` with parameters
9. `servo_calcs.cpp` (line 89): **Tries to get joint model group - CRASH**

### The Issue
Parameters are declared with defaults **before** any user-provided YAML files or command-line arguments can override them. The `declare_parameter` call uses the default value from the struct if the parameter hasn't been set yet. This happens during `ServoNode` construction, before ROS parameter loading completes.

## Why Our Attempts Failed

### Attempt 1: YAML Files with `move_group_name: manipulator`
- **Result**: Failed
- **Why**: The parameter declaration happens with the default value BEFORE the YAML file is loaded

### Attempt 2: NodeOptions with arguments (`-p move_group_name:=manipulator`)
- **Result**: Failed  
- **Why**: Same issue - parameters are declared before these are processed

### Attempt 3: Custom C++ Node (`za6_servo_node.cpp`)
- **Result**: Failed
- **Why**: Even passing parameters via `NodeOptions` doesn't help because the `declare()` function uses the struct defaults

### Attempt 4: Parameter file with proper ROS 2 wrapper (`ros__parameters`)
- **Result**: Failed
- **Why**: The parameter declaration still happens before the file is loaded

## Potential Solutions

### Option A: Rebuild moveit_servo with Changed Default
1. Clone moveit2 source
2. Edit `include/moveit_servo/servo_parameters.h` line 85: `std::string move_group_name{ "manipulator" };`
3. Rebuild the package
4. Install in Docker container

### Option B: Use MoveIt Servo's Composable Node API
- Possibly use the composable node interface if available
- Would require investigating the composable node API

### Option C: Create Minimal Standalone Servo
- Re-implement critical servo functionality without using the hardcoded default
- Most work, most control

### Option D: Parameter Namespace Override
- Try using a different parameter namespace
- Investigate if `declare()` can be called with different defaults

### Option E: Patch the Installed Package
- Binary patch the installed .so file (risky, not recommended)

## Recommended Next Steps

1. **Try Option A**: Rebuild moveit_servo with `"manipulator"` as default
2. **Investigate composable node**: Check if there's a different API that allows parameter pre-loading
3. **Contact MoveIt maintainers**: Report this as a limitation for non-Panda arms
4. **Consider alternative**: Use direct Cartesian velocity control instead of MoveIt Servo

## Files to Modify (Option A)

### 1. Edit `/home/pathpilot/Temp/moveit2/moveit_ros/moveit_servo/include/moveit_servo/servo_parameters.h`
Line 85: Change
```cpp
std::string move_group_name{ "panda_arm" };
```
to
```cpp
std::string move_group_name{ "manipulator" };
```

### 2. Also check line 75:
```cpp
std::string command_out_topic{ "/panda_arm_controller/joint_trajectory" };
```
Should probably be changed to a generic value or parameterized.

### 3. Line 67:
```cpp
std::string robot_link_command_frame{ "panda_link0" };
```
Should also be reviewed.

## Build Instructions (Option A)

Inside the Docker container:
```bash
cd /home/pathpilot/Temp/moveit2
colcon build --packages-select moveit_ros_moveit_servo
source install/setup.bash
```

Then update the Dockerfile or install the modified package.

## Alternative: Use Different Parameter Namespace

Try using `"manipulator"` or `"za6_arm"` as the namespace when calling `makeServoParameters`:
```cpp
auto servo_parameters = moveit_servo::ServoParameters::makeServoParameters(node_, "za6_servo");
```
But this still requires setting `move_group_name` parameter BEFORE constructing ServoNode, which seems impossible with the current architecture.

## Conclusion

The architecture of MoveIt Servo makes it difficult to override the `move_group_name` parameter from `"panda_arm"` to `"manipulator"` because:

1. The parameter is declared with its default value during `ServoNode` construction
2. This happens before any YAML files or command-line arguments can override it
3. The error occurs in `ServoCalcs` constructor before the servo even starts

The cleanest solution is **Option A**: Rebuild moveit_servo with `"manipulator"` as the default.


