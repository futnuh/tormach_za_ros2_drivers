# Capturing Poses During Teleoperation

## Overview

This guide shows how to capture the current end-effector pose during teleoperation and use it to define frames in `user_frames.yaml`.

## Quick Steps

### 1. Launch System with Teleoperation

```bash
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

### 2. Move Robot to Desired Position

Use your gamepad to teleoperate the robot to the desired position:
- Position the end-effector where you want the frame
- Hold the robot steady at the desired pose
- Make sure the orientation is correct

### 3. Capture Current Pose

**In another terminal:**
```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
source install/setup.bash

ros2 run za6_moveit_config get_current_pose.py
```

**Output Example:**
```
============================================================
Current End-Effector Pose
============================================================
End-Effector Link: grasp_link
Parent Frame: world

Position (meters):
  X: 0.500000
  Y: 0.000000
  Z: 0.750000

Orientation (radians):
  Roll:  0.000000
  Pitch: 0.000000
  Yaw:   0.000000

Orientation (degrees):
  Roll:  0.00°
  Pitch: 0.00°
  Yaw:   0.00°

============================================================
YAML Format (copy this to user_frames.yaml):
============================================================

pose: [0.500000, 0.000000, 0.750000, 0.000000, 0.000000, 0.000000]

Full YAML entry:
# Frame: my_frame
my_frame:
  parent_frame: world
  pose: [0.500000, 0.000000, 0.750000, 0.000000, 0.000000, 0.000000]
  description: "Frame captured via teleoperation"

============================================================
```

### 4. Add to user_frames.yaml

Copy the pose array from the output and add it to `za6_moveit_config/config/user_frames.yaml`:

```yaml
my_captured_frame:
  parent_frame: world
  pose: [0.500000, 0.000000, 0.750000, 0.000000, 0.000000, 0.000000]
  description: "Frame captured via teleoperation"
```

### 5. Store to Warehouse

```bash
ros2 run za6_moveit_config store_frames_to_warehouse.py
```

## Advanced Usage

### Custom End-Effector Link

```bash
ros2 run za6_moveit_config get_current_pose.py --ee-link custom_link
```

### Custom Parent Frame

```bash
ros2 run za6_moveit_config get_current_pose.py --parent-frame base_link
```

## Alternative: Get Pose from RViz

If you want to see the pose in RViz:

1. In RViz, select the end-effector link
2. Check the TF display to see the transform
3. Or use the "Measure" tool to see distances

## Alternative: Get Joint State Instead

If you want to capture joint state instead of pose:

1. Get current joint positions:
   ```bash
   ros2 topic echo /joint_states --once
   ```

2. Use the joint positions in user_frames.yaml:
   ```yaml
   my_joint_frame:
     parent_frame: world
     joint_state:
       name: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6]
       position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # Paste joint positions here
     ee_link: grasp_link
     description: "Frame captured via joint state"
   ```

## Tips

- **Hold steady**: Keep the robot still when capturing the pose
- **Multiple captures**: Capture the pose multiple times to verify consistency
- **Check orientation**: Make sure the orientation (roll, pitch, yaw) is correct
- **Save before capture**: Make sure you're at the exact position you want before capturing

