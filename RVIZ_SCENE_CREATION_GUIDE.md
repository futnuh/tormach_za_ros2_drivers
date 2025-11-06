# Creating and Managing Scenes in RViz

## Overview

RViz Motion Planning plugin allows you to create, modify, and save planning scenes. Scenes can contain:
- Robot states
- Objects (boxes, spheres, cylinders, meshes)
- Collision objects
- User-defined frames (represented as objects)

## Step-by-Step: Create a New Scene in RViz

### Prerequisites

1. **Launch with warehouse enabled:**
   ```bash
   ros2 launch za6_moveit_config teleop_hardware.launch.py \
     use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
     use_rviz:=true \
     servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
     db:=true
   ```

2. **Wait for RViz to fully load** - You should see the robot model and Motion Planning plugin.

### Creating a New Scene

#### Step 1: Open Motion Planning Plugin

1. In RViz, find the **"Motion Planning"** display (should be visible by default)
2. If not visible:
   - Click **"Add"** button at bottom
   - Select **"Motion Planning"** (under `moveit_rviz_plugin`)

#### Step 2: Add Objects to Scene

1. Go to **"Scene Robot"** tab in the Motion Planning panel
2. Click **"Add"** button
3. Choose object type:
   - **Box** - Rectangular objects
   - **Sphere** - Round objects  
   - **Cylinder** - Cylindrical objects
   - **Mesh** - Custom mesh files

4. **Configure the object:**
   - **Id:** Name your object (e.g., "table_frame", "fixture_1")
   - **Position:** Set X, Y, Z coordinates (in meters)
   - **Orientation:** Set roll, pitch, yaw (in radians) or use quaternion
   - **Dimensions:** Set size of object
   - **Note:** Objects are added relative to the planning scene frame (usually "world" if RViz Fixed Frame is set to "world")

5. **Click "Add Object"** - Object appears in the scene

#### Step 3: Position Objects Visually (Optional)

1. Enable **"Interact"** tool in RViz toolbar
2. Click on the object
3. Use the interactive markers (arrows, rings) to drag/rotate the object
4. Object position updates in real-time

#### Step 4: Save Scene to Warehouse

1. Go to **"Planning"** tab in Motion Planning plugin
2. Scroll down to **"Scene"** section
3. Click **"Save Scene"** button
4. **Enter scene name** (e.g., "my_scene", "user_frames", "workspace_setup")
5. Click **"OK"** or press Enter
6. Scene is saved to the warehouse database!

**Verification:**
- You should see a success message or confirmation
- Scene appears in "Load Scene" dropdown for future use

### Loading a Saved Scene

1. Go to **"Planning"** tab
2. In **"Scene"** section, click **"Load Scene"** dropdown
3. Select your saved scene name
4. Scene loads and objects reappear!

### Managing Objects in Scene

#### Modify Existing Objects

1. In **"Scene Robot"** tab
2. Select object from list
3. Modify properties (position, orientation, dimensions)
4. Click **"Update Object"**

#### Remove Objects

1. In **"Scene Robot"** tab
2. Select object from list
3. Click **"Remove"** button

#### Clear Entire Scene

1. In **"Planning"** tab
2. Click **"Clear"** button (clears current scene but doesn't delete saved scenes)

## Creating Frames as Objects

To create user frames in RViz:

1. **Add a small box** (e.g., 0.1m x 0.1m x 0.1m)
2. **Position it** at your desired frame location
3. **Name it** with frame prefix (e.g., "frame_table", "frame_fixture")
4. **Set orientation** to match your frame's axes
5. **Save scene** with a descriptive name

### Example: Creating a Table Frame

1. Add → Box
2. Id: `frame_table`
3. Position: X=0.5, Y=0.0, Z=0.75
4. Dimensions: 0.1, 0.1, 0.1 (10cm cube to mark the frame)
5. Orientation: 0, 0, 0
6. Frame: world
7. Click "Add Object"
8. Save Scene → Name: "user_frames"

## Tips and Best Practices

### Organizing Scenes

- **Use descriptive names:** "workspace_setup", "fixtures_layout", "calibration_frames"
- **One scene per workspace configuration**
- **Save frequently** as you build your scene

### Frame Visualization

- Use **small boxes** (5-10cm cubes) to mark frame origins
- Use **axes** visualization if available (Add → Axes) to show frame orientation
- Use **different colors** for different frame types (work areas vs fixtures)

### Scene Management

- **Keep a clean scene:** Remove unused objects
- **Version your scenes:** "workspace_v1", "workspace_v2"
- **Document your scenes:** Add comments/notes about what each object represents

### Integration with Warehouse

- **All saved scenes** are stored in `~/.ros/warehouse/moveit_warehouse.sqlite`
- **Scenes persist** across restarts when warehouse is enabled
- **Backup database** regularly: `cp ~/.ros/warehouse/moveit_warehouse.sqlite ~/backup.sqlite`

## Keyboard Shortcuts and Tips

- **G** - Toggle grid display
- **Q, W, E, R, T, Y** - Switch between tools
- **Right-click drag** - Rotate view
- **Middle-click drag** - Pan view
- **Scroll wheel** - Zoom

## Troubleshooting

### Scene Doesn't Save

- Check warehouse is running (`db:=true`)
- Verify `/apply_planning_scene` service exists: `ros2 service list | grep scene`
- Check RViz console for error messages

### Objects Don't Appear

- Verify frame is correct ("world" typically)
- Check object dimensions aren't too small (at least 0.01m)
- Ensure "Scene Robot" display is enabled in RViz

### Can't Load Saved Scene

- Verify scene was actually saved (check warehouse database)
- Try reloading RViz config: File → Open Config
- Check service is available: `ros2 service list | grep warehouse`

### Objects Disappear After Restart

- Make sure warehouse was enabled (`db:=true`) when you saved
- Verify database file exists: `ls ~/.ros/warehouse/moveit_warehouse.sqlite`
- Try loading scene manually from "Load Scene" dropdown

### Issue: Database Schema Error When Saving Scene

**Error:**
```
[ERROR] [moveit_ros_visualization.motion_planning_frame_objects]: 
Prepare statement for removeMessages() failed no such column: M_planning_scene_id
```

**Solution:**
The warehouse database schema isn't fully initialized. Fix it by:

1. **Delete the database** (it will recreate with proper schema):
   ```bash
   rm ~/.ros/warehouse/moveit_warehouse.sqlite
   ```

2. **The schema will be created automatically** when you save your first scene from RViz or when you use warehouse services for the first time.

**Note:** For user frames, we recommend using `publish_frame_markers.py` which creates visual-only markers (not collision objects) with clear x, y, z axes orientation.

## Advanced: Programmatic Scene Creation

You can also create scenes programmatically using ROS2 services:

```bash
# Get current scene
ros2 service call /get_planning_scene moveit_msgs/srv/GetPlanningScene

# Apply a scene (modify the message and call)
ros2 service call /apply_planning_scene moveit_msgs/srv/ApplyPlanningScene
```

Or use the frame marker publisher for visual-only frames:
```bash
ros2 run za6_moveit_config publish_frame_markers.py
```

This script reads `user_frames.yaml` and publishes visualization markers with colored axes (Red=X, Green=Y, Blue=Z) that are NOT collision objects.

