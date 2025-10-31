# Debugging MoveIt Servo Issues - Checklist

## 1. Check if Servo is Publishing
```bash
# For servo teleoperation (streaming controller)
ros2 topic hz /streaming_controller/commands

# For trajectory-based control
ros2 topic hz /joint_trajectory_controller/joint_trajectory
```
**Expected**: Should see frequent messages (~100 Hz when moving gamepad for streaming controller)
**If no messages**: Servo is paused/stopped or not configured correctly

## 2. Check Servo Status
```bash
ros2 topic echo /servo_node/status
```
**Status Codes**:
- `0` = Stopped/Paused
- `1` = Running
- **If status is 0**: Call unpause service

## 3. Check Gamepad Input
```bash
ros2 topic echo /servo_node/delta_twist_cmds
```
**Expected**: See twist commands when moving gamepad
**If no messages**: Gamepad isn't sending commands or servo isn't subscribed

## 4. Check Servo Parameters
```bash
# Check which topic servo is publishing to
ros2 param get /servo_node moveit_servo.command_out_topic

# Check halt settings
ros2 param get /servo_node moveit_servo.halt_all_joints_in_cartesian_mode
```
**Expected**:
- `command_out_topic` = `/streaming_controller/commands` (for servo teleoperation) or `/joint_trajectory_controller/joint_trajectory` (for trajectory control)
- `halt_all_joints_in_cartesian_mode` = `False`

## 5. Check Controller State
```bash
ros2 topic echo /joint_trajectory_controller/controller_state
```
**Expected**: See controller state showing active controllers
**Check**: Is the controller actually executing trajectories?

## 6. Check Collision Detection
```bash
ros2 topic echo /servo_node/collision_velocity_scale
```
**Expected**: `data: 1.0` (full speed allowed)
**If lower**: Collision detection is reducing speed

## 7. View Servo Debug Messages
Look in the launch terminal for messages like:
- "Publishing command"
- "Servo paused"
- "Collision detected"
- Any ERROR or WARN messages

## 8. Most Likely Issues

### Issue: Servo Status = 0 (Paused)
**Fix**:
```bash
ros2 service call /servo_node/unpause_servo std_srvs/srv/Trigger
ros2 service call /servo_node/start_servo std_srvs/srv/Trigger
```

### Issue: Wrong Output Topic
**Check**: 
```bash
ros2 node info /servo_node
```
Look at "Publishers:" section - should publish to `/streaming_controller/commands` (for servo teleoperation) or `/joint_trajectory_controller/joint_trajectory` (for trajectory control)

**Fix**: Check launch file has correct parameter:
```python
# For servo teleoperation
"moveit_servo.command_out_topic": "/streaming_controller/commands"
"moveit_servo.command_out_type": "std_msgs/Float64MultiArray"
"moveit_servo.publish_joint_positions": True
"moveit_servo.publish_joint_velocities": False
```

### Issue: halt_all_joints_in_cartesian_mode = True
**Check**:
```bash
ros2 param get /servo_node moveit_servo.halt_all_joints_in_cartesian_mode
```

**Fix**:
```bash
ros2 param set /servo_node moveit_servo.halt_all_joints_in_cartesian_mode false
```

### Issue: Controller Not Active
**Check**:
```bash
ros2 control list_controllers
```

**Expected**: 
- For servo teleoperation: `streaming_controller` should be `active` when servo is enabled
- For trajectory control: `joint_trajectory_controller` should be `active`
**If inactive**: Launch should activate it automatically, or check gamepad button to enable servo mode

## 9. Quick Test: Manual Servo Commands

Test if servo responds to direct commands:
```bash
# Send a test trajectory
ros2 topic pub /joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "header:
  stamp:
    sec: 0
    nanosec: 0
  frame_id: ''
points:
- positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  time_from_start:
    sec: 0
    nanosec: 100000000
joint_names:
- joint_1
- joint_2
- joint_3
- joint_4
- joint_5
- joint_6" -1
```

If robot moves from manual command but not from gamepad → Servo is the problem
If robot doesn't move from manual command → Controller/Simulation is the problem

## 10. Summary of Current Status
✅ **RESOLVED**: Servo is now working correctly with hardware teleoperation.

**Current working configuration**:
- ✅ Gamepad publishing commands to servo (`/servo_node/delta_twist_cmds` and `/servo_node/delta_joint_cmds`)
- ✅ Servo configured to publish to `/streaming_controller/commands` for teleoperation
- ✅ Controller switching works between `streaming_controller` (teleop) and `joint_trajectory_controller` (planning)
- ✅ Servo parameters properly configured via `servo_config.yaml` and inline launch parameters
- ✅ Hardware teleoperation fully functional

**For detailed integration documentation, see**: `TELEOP_SERVO_INTEGRATION.md`

