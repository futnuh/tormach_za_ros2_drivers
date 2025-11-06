# Testing Warehouse Frame Storage

## Overview

This guide shows how to test the warehouse storage system for user frames. The system allows you to:
- Store frames in the warehouse database (persistent)
- Load frames from the warehouse
- Publish visual markers from warehouse-stored frames
- Verify frames persist across restarts

## Prerequisites

**Note:** These commands assume you're already inside the docker container.
If you're on the host, wrap commands with: `docker exec ros2-devel bash -c "..."`

1. **Build the package:**
   ```bash
   cd /home/pathpilot/Temp/tormach_za_ros2_drivers
   colcon build --packages-select za6_moveit_config
   source install/setup.bash
   ```

2. **Have frames defined in YAML:**
   ```bash
   # Check that user_frames.yaml exists and has frames
   cat za6_moveit_config/config/user_frames.yaml
   ```

## Step-by-Step Testing

### Step 1: Launch System with Warehouse

**Terminal 1 - Launch system:**
```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
source install/setup.bash

ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

**Wait for:**
- All nodes to start (you should see `moveit_warehouse` in the process list)
- No errors about missing warehouse services
- System fully initialized

### Step 2: Store Frames to Warehouse

**Terminal 2 - Store frames:**
```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
source install/setup.bash

ros2 run za6_moveit_config store_frames_to_warehouse.py
```

**Expected output:**
```
[INFO] [frame_warehouse_storer]: Waiting for planning scene services...
[INFO] [frame_warehouse_storer]: Loaded X frames from ...
[INFO] [frame_warehouse_storer]: Computing forward kinematics for frame 'home_frame' using grasp_link
[INFO] [frame_warehouse_storer]: Prepared X frames for storage
[INFO] [frame_warehouse_storer]: Successfully stored X frames in warehouse as scene 'user_frames'!
[INFO] [frame_warehouse_storer]: Frame definitions also saved to /home/pathpilot/.ros/warehouse/user_frames.json
```

**Verify storage:**
```bash
# Check that backup JSON file was created
ls -lh ~/.ros/warehouse/user_frames.json

# Check database file exists and has data
ls -lh ~/.ros/warehouse/moveit_warehouse.sqlite
```

### Step 3: Verify Frames in Warehouse

**Terminal 2 - Load frames:**
```bash
# Load frames from warehouse backup file
ros2 run za6_moveit_config load_frames_from_warehouse.py
```

**Expected output:**
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

**Note:** In ROS2 MoveIt2, warehouse scenes are stored when `ApplyPlanningScene` is called, 
but programmatic listing/getting of scenes isn't exposed as separate services. 
Frames are loaded from the backup JSON file created during storage.

### Step 4: Publish Markers from Warehouse

**Terminal 2 - Publish markers:**
```bash
ros2 run za6_moveit_config publish_frame_markers.py --from-warehouse
```

**Expected output:**
```
[INFO] [frame_marker_publisher]: Loaded X frames from warehouse
[INFO] [frame_marker_publisher]: Publishing frame markers...
```

**In RViz (Terminal 1):**
1. Add "MarkerArray" display:
   - Click "Add" → "By topic" → `/user_frames`
   - Or "Add" → "By display type" → "MarkerArray"
   - Set topic to `/user_frames`

2. You should see:
   - **Red arrows** pointing along X axis
   - **Green arrows** pointing along Y axis  
   - **Blue arrows** pointing along Z axis
   - **Text labels** showing frame names
   - All at the positions defined in your frames!

### Step 5: Test Persistence

**Shut down everything:**
1. Ctrl+C in Terminal 1 (launch)
2. Ctrl+C in Terminal 2 (marker publisher)

**Restart system:**
```bash
# Terminal 1 - Launch again
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

**Load frames from warehouse:**
```bash
# Terminal 2 - Load and verify
ros2 run za6_moveit_config load_frames_from_warehouse.py
```

**Expected:** Frames should still be there!

**Publish markers from warehouse:**
```bash
# Terminal 2 - Publish markers
ros2 run za6_moveit_config publish_frame_markers.py --from-warehouse
```

**Expected:** Markers should appear in RViz exactly as before!

### Step 6: Export Frames to YAML

**Terminal 2 - Export warehouse frames to YAML:**
```bash
ros2 run za6_moveit_config load_frames_from_warehouse.py \
  --export-yaml ~/test_frames_from_warehouse.yaml

# Verify exported file
cat ~/test_frames_from_warehouse.yaml
```

**Expected:** YAML file with frames from warehouse

## Quick Test Checklist

- [ ] Package builds without errors
- [ ] Warehouse starts successfully (`db:=true`)
- [ ] `store_frames_to_warehouse.py` completes successfully
- [ ] Backup JSON file created at `~/.ros/warehouse/user_frames.json`
- [ ] `load_frames_from_warehouse.py` loads frames correctly
- [ ] `publish_frame_markers.py --from-warehouse` works
- [ ] Markers appear in RViz with colored axes
- [ ] Frames persist after restart (warehouse still has them)
- [ ] Export to YAML works correctly

## Troubleshooting

### Issue: Warehouse Service Not Available

**Error:**
```
Warehouse save_scene service not available. Make sure warehouse is running (db:=true)
```

**Solution:**
- Make sure you launched with `db:=true`
- Wait for warehouse node to fully start
- Check: `ros2 node list | grep warehouse`

### Issue: No Frames Found in Warehouse

**Error:**
```
Scene 'user_frames' not found in warehouse
```

**Solution:**
- Run `store_frames_to_warehouse.py` first
- Verify warehouse is enabled: `db:=true`
- Check backup file exists: `ls ~/.ros/warehouse/user_frames.json`

### Issue: Markers Don't Appear in RViz

**Check:**
1. Is marker publisher running?
2. Did you add MarkerArray display in RViz?
3. Is topic set to `/user_frames`?
4. Check topic exists: `ros2 topic list | grep user_frames`
5. Check topic has data: `ros2 topic echo /user_frames --once`

### Issue: Forward Kinematics Fails

**Error:**
```
Failed to compute FK for frame 'home_frame'
```

**Solution:**
- Make sure `move_group` is running
- Wait a few seconds after launch for MoveIt to initialize
- Check FK service: `ros2 service list | grep compute_fk`

## Advanced Testing

### Test Both Storage Methods

1. **Store from YAML to warehouse:**
   ```bash
   ros2 run za6_moveit_config store_frames_to_warehouse.py
   ```

2. **Load from warehouse:**
   ```bash
   ros2 run za6_moveit_config load_frames_from_warehouse.py
   ```

3. **Publish from warehouse:**
   ```bash
   ros2 run za6_moveit_config publish_frame_markers.py --from-warehouse
   ```

4. **Compare with YAML source:**
   ```bash
   # Publish from YAML
   ros2 run za6_moveit_config publish_frame_markers.py
   
   # Publish from warehouse
   ros2 run za6_moveit_config publish_frame_markers.py --from-warehouse
   ```

Both should show the same frames!

### Test Database Backup/Restore

1. **Backup database:**
   ```bash
   cp ~/.ros/warehouse/moveit_warehouse.sqlite ~/backup_warehouse.sqlite
   cp ~/.ros/warehouse/user_frames.json ~/backup_user_frames.json
   ```

2. **Delete database:**
   ```bash
   rm ~/.ros/warehouse/moveit_warehouse.sqlite
   rm ~/.ros/warehouse/user_frames.json
   ```

3. **Restore from backup:**
   ```bash
   cp ~/backup_warehouse.sqlite ~/.ros/warehouse/moveit_warehouse.sqlite
   cp ~/backup_user_frames.json ~/.ros/warehouse/user_frames.json
   ```

4. **Verify frames restored:**
   ```bash
   ros2 run za6_moveit_config load_frames_from_warehouse.py
   ```

## Success Criteria

✅ Frames stored to warehouse successfully  
✅ Backup JSON file created  
✅ Frames loadable from warehouse  
✅ Markers publish correctly from warehouse  
✅ Frames persist across restarts  
✅ Export to YAML works  
✅ Visual markers show correct axes (Red=X, Green=Y, Blue=Z)  
✅ Markers are NOT collision objects (planner ignores them)

