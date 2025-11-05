# Testing User Frames Guide

## Quick Test Steps

### Step 1: Define Test Frames

#### Option A: Capture Pose via Teleoperation (Recommended)

1. **Launch system with teleoperation:**
   ```bash
   ros2 launch za6_moveit_config teleop_hardware.launch.py \
     use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
     use_rviz:=true \
     servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
     db:=true
   ```

2. **Use gamepad to move robot to desired position:**
   - Use teleoperation to position end-effector where you want the frame
   - Hold the robot steady at the desired pose

3. **Capture current pose (in another terminal):**
   ```bash
   cd /home/pathpilot/Temp/tormach_za_ros2_drivers
   source install/setup.bash
   
   ros2 run za6_moveit_config get_current_pose.py
   ```

4. **Output will show:**
   - Current position (x, y, z)
   - Current orientation (roll, pitch, yaw) in radians and degrees
   - YAML format ready to copy to user_frames.yaml

5. **Copy the pose array to user_frames.yaml:**
   ```yaml
   test_table_frame:
     parent_frame: world
     pose: [0.5, 0.0, 0.75, 0, 0, 0]  # Paste the pose array here
     description: "Test table frame (captured via teleoperation)"
   ```

#### Option B: Manual Entry

Edit `za6_moveit_config/config/user_frames.yaml` and add test frames manually:

```yaml
---
# Test frames - mix of poses and joint states

# Test pose-based frame
test_table_frame:
  parent_frame: world
  pose: [0.5, 0.0, 0.75, 0, 0, 0]
  description: "Test table frame (pose-based)"

# Test joint-state frame
test_home_frame:
  parent_frame: world
  joint_state:
    name: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6]
    position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  ee_link: grasp_link
  description: "Test home frame (joint-state based)"
```

### Step 2: Build the Package

```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
colcon build --packages-select za6_moveit_config
source install/setup.bash
```

### Step 3: Launch System with Warehouse

```bash
# Launch with warehouse enabled
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

**Wait for all nodes to start** (you should see `moveit_warehouse` in the running processes).

### Step 4: Publish Frame Markers

In a **new terminal**:

```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
source install/setup.bash

# Publish frame markers
ros2 run za6_moveit_config publish_frame_markers.py
```

**Expected output:**
```
[INFO] [frame_marker_publisher]: Loaded X frames from ...
[INFO] [frame_marker_publisher]: Publishing frame markers...
```

### Step 5: Verify in RViz

1. **Add MarkerArray Display:**
   - Click "Add" → "By topic" → `/user_frames`
   - Or "Add" → "By display type" → "MarkerArray"
   - Set topic to `/user_frames`

2. **You should see:**
   - **Red arrows** pointing along X axis
   - **Green arrows** pointing along Y axis
   - **Blue arrows** pointing along Z axis
   - **Text labels** showing frame names
   - All at the positions defined in your frames!

3. **Check TF Tree (if using Method 1):**
   ```bash
   ros2 run tf2_tools view_frames
   # Opens frames.pdf - check for your frame names
   ```

### Step 6: Verify Warehouse Storage

```bash
# Check if database exists
ls -lh ~/.ros/warehouse/moveit_warehouse.sqlite

# Check database size (should increase after saving frames)
# The database file will have data stored in it
```

### Step 7: Test Persistence

1. **Shut down everything** (Ctrl+C on launch)

2. **Launch again with warehouse:**
   ```bash
   ros2 launch za6_moveit_config teleop_hardware.launch.py db:=true ...
   ```

3. **Load scene in RViz:**
   - Go to Motion Planning plugin → "Planning" tab
   - Click "Load Scene"
   - Select your saved scene (if you named it)
   - Frames should reappear!

   OR frames should automatically appear if they're part of the default scene.

## Troubleshooting

### Issue: FK Service Not Available

**Error:**
```
[WARN] Forward kinematics service not available. Joint-state frames will be skipped.
```

**Solution:**
- Make sure `move_group` is running
- The FK service needs MoveIt to be fully initialized
- Wait a few seconds after launching before running the save script

### Issue: No Frames Appear in RViz

**Check:**
1. Did the save script complete successfully?
2. Are frames visible in Scene Robot tab?
3. Try adding a frame manually in RViz to verify the scene system works
4. Check RViz logs for errors

### Issue: Frames Not Persisting

**Check:**
1. Is warehouse enabled (`db:=true`)?
2. Did you actually save to warehouse (run the save script)?
3. Check database file exists: `ls -lh ~/.ros/warehouse/moveit_warehouse.sqlite`
4. Try deleting the database and recreating (it will rebuild on first save)

### Issue: Joint State Frames Fail

**Error:**
```
[ERROR] Failed to compute FK for frame 'test_home_frame'
```

**Solution:**
- Make sure move_group is running and fully initialized
- Check that joint names match your robot configuration
- Verify `ee_link` is correct (defaults to `grasp_link`)
- Try with a known valid joint position (like home position)

## Advanced Testing

### Test Both Frame Types Together

Create a mixed YAML:

```yaml
---
# Mix pose and joint-state frames
pose_frame_1:
  parent_frame: world
  pose: [0.3, 0.2, 0.5, 0, 0, 0]
  description: "Pose frame 1"

joint_frame_1:
  parent_frame: world
  joint_state:
    name: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6]
    position: [0.5, -0.5, 0.5, -0.5, 0.5, 0.0]
  ee_link: grasp_link
  description: "Joint frame 1"

pose_frame_2:
  parent_frame: world
  pose: [0.6, 0.4, 0.8, 0, 0, 1.57]
  description: "Pose frame 2"

joint_frame_2:
  parent_frame: world
  joint_state:
    name: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6]
    position: [1.0, -1.0, 1.0, -1.0, 1.0, 0.5]
  ee_link: grasp_link
  description: "Joint frame 2"
```

Save and verify all frames appear correctly.

### Verify Forward Kinematics

Test that joint positions convert correctly:

1. Move robot to a known position (use waypoints or manual control)
2. Get current joint state:
   ```bash
   ros2 topic echo /joint_states --once
   ```
3. Add that joint state to your frames YAML
4. Save to warehouse
5. Check if the computed pose matches where the robot actually is

## Success Criteria

✅ Frames defined in YAML are loaded  
✅ Pose-based frames appear at correct locations  
✅ Joint-state frames compute FK correctly  
✅ All frames saved to warehouse successfully  
✅ Frames visible in RViz planning scene  
✅ Frames persist across restarts  
✅ TF transforms published correctly (for pose frames)

