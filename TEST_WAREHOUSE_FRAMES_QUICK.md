# Quick Test Commands (Inside Docker Container)

## Prerequisites

Make sure you're in the docker container and have sourced the workspace:
```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
source install/setup.bash
```

## Step 1: Build Package

```bash
colcon build --packages-select za6_moveit_config
source install/setup.bash
```

## Step 2: Launch System with Warehouse

**Terminal 1:**
```bash
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

**Wait for:** All nodes to start, warehouse to initialize

## Step 3: Store Frames to Warehouse

**Terminal 2 (new terminal in docker):**
```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
source install/setup.bash

# Store frames (correct command - full package name)
ros2 run za6_moveit_config store_frames_to_warehouse.py
```

**Note:** The database schema errors in RViz are expected on first use. 
The schema will be created automatically when you save your first scene.

**Expected:**
```
[INFO] [frame_warehouse_storer]: Waiting for planning scene services...
[INFO] [frame_warehouse_storer]: Loaded X frames from ...
[INFO] [frame_warehouse_storer]: Computing forward kinematics for frame 'home_frame' using grasp_link
[INFO] [frame_warehouse_storer]: Prepared X frames for storage
[INFO] [frame_warehouse_storer]: Successfully stored X frames in warehouse as scene 'user_frames'!
[INFO] [frame_warehouse_storer]: Note: Scene is stored in warehouse and can be loaded via RViz Motion Planning plugin
[INFO] [frame_warehouse_storer]: Frame definitions also saved to /home/pathpilot/.ros/warehouse/user_frames.json for backup
```

## Step 4: Verify Storage

```bash
# Check backup file exists
ls -lh ~/.ros/warehouse/user_frames.json

# Check database exists
ls -lh ~/.ros/warehouse/moveit_warehouse.sqlite

# View stored frames (quick check)
cat ~/.ros/warehouse/user_frames.json | head -30
```

## Step 5: Load Frames from Warehouse

```bash
ros2 run za6_moveit_config load_frames_from_warehouse.py
```

**Expected:**
```
[INFO] [frame_warehouse_loader]: Loading frames from warehouse backup file...
[INFO] [frame_warehouse_loader]: Loaded X frames from warehouse backup file
[INFO] [frame_warehouse_loader]: Note: Scene 'user_frames' is also stored in warehouse database
[INFO] [frame_warehouse_loader]:       Load it via RViz Motion Planning plugin → Planning → Load Scene
[INFO] [frame_warehouse_loader]: Loaded X frames from warehouse:
  - table_frame: [0.500, 0.000, 0.750]
  - fixture_frame: [0.300, 0.400, 0.500]
  ...
```

## Step 6: Publish Markers from Warehouse

```bash
ros2 run za6_moveit_config publish_frame_markers.py --from-warehouse
```

**Expected:**
```
[INFO] [frame_marker_publisher]: Loaded X frames from warehouse
[INFO] [frame_marker_publisher]: Publishing frame markers...
```

**In RViz (Terminal 1):**
1. Add "MarkerArray" display
2. Set topic to `/user_frames`
3. You should see colored axes (Red=X, Green=Y, Blue=Z)

## Step 7: Export to YAML

```bash
ros2 run za6_moveit_config load_frames_from_warehouse.py \
  --export-yaml ~/test_frames_from_warehouse.yaml

# Verify exported file
cat ~/test_frames_from_warehouse.yaml
```

## Step 8: Test Persistence

**Shut down everything (Ctrl+C in both terminals)**

**Restart system (Terminal 1):**
```bash
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

**Load frames (Terminal 2):**
```bash
ros2 run za6_moveit_config load_frames_from_warehouse.py
```

**Expected:** Frames still available!

**Publish markers:**
```bash
ros2 run za6_moveit_config publish_frame_markers.py --from-warehouse
```

**Expected:** Markers appear in RViz!

## Quick Verification Commands

```bash
# Check services are available
ros2 service list | grep scene

# Check topic is publishing
ros2 topic echo /user_frames --once

# Check warehouse services
ros2 service list | grep warehouse

# Check backup file
cat ~/.ros/warehouse/user_frames.json | jq .  # if jq is installed
```

## Troubleshooting

**Issue: Script not found**
```bash
# Rebuild package
colcon build --packages-select za6_moveit_config
source install/setup.bash

# Verify script exists
ros2 pkg executables za6_moveit_config
```

**Issue: Services not available**
```bash
# Check warehouse is running
ros2 node list | grep warehouse

# Check services
ros2 service list | grep -E '(scene|warehouse)'
```

**Issue: FK service not available**
```bash
# Check move_group is running
ros2 node list | grep move_group

# Check FK service
ros2 service list | grep compute_fk
```

