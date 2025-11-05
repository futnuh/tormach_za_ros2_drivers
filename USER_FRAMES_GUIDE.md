# User Frames Guide for ZA6 Robot

## Overview

User frames (also called reference frames or coordinate frames) allow you to define custom coordinate systems in your robot workspace. These frames are useful for:

- Defining work positions (table tops, fixtures, etc.)
- Storing calibration points
- Organizing waypoints relative to specific locations
- Planning operations relative to fixed objects

## Method 1: YAML Configuration + Launch File (Recommended)

### Step 1: Define Frames in YAML

Edit `za6_moveit_config/config/user_frames.yaml`:

You can define frames in **two ways**:

**Option A: Using Cartesian Pose (direct)**
```yaml
table_frame:
  parent_frame: world
  pose: [0.5, 0.0, 0.75, 0, 0, 0]  # [x, y, z, roll, pitch, yaw]
  description: "Main work table surface"
```

**Option B: Using Joint Positions (computed via forward kinematics)**
```yaml
home_frame:
  parent_frame: world
  joint_state:
    name: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6]
    position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  ee_link: grasp_link  # Optional: defaults to grasp_link
  description: "Home position frame (computed from joint angles)"
```

**You can mix both types in the same file!**

**Pose Format:**
- Position: `[x, y, z]` in meters
- Orientation: `[roll, pitch, yaw]` in radians
- Total: `[x, y, z, roll, pitch, yaw]`
- **Works with:** Launch file (static transforms) ✅ and Warehouse ✅

**Joint State Format:**
- `name`: List of joint names (e.g., `[joint_1, joint_2, ...]`)
- `position`: List of joint positions in radians (same order as names)
- `ee_link`: (Optional) End effector link to use for pose computation (defaults to `grasp_link`)
- **Works with:** Visual markers (Method 2) ✅ (requires MoveIt running for forward kinematics)
- **Note:** Static transform publishers (Method 1 launch file) require poses, so joint-state frames must use Method 2 (visual markers) instead.

### Step 2: Launch User Frames

Include the user frames launch file in your main launch:

**Option A: Add to `za6_bringup/launch/bringup.launch`:**

```xml
<!-- User-defined frames -->
<include file="$(var moveit_config_package_launch)/user_frames.launch.py"/>
```

**Option B: Launch separately:**

```bash
ros2 launch za6_moveit_config user_frames.launch.py
```

**Option C: Include in teleop launch:**

Add to `teleop_hardware.launch.py`:

```python
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

# User frames
user_frames_launch = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        PathJoinSubstitution([cfg_pkg, "launch", "user_frames.launch.py"])
    ),
)
```

## Method 2: Visual Markers (Recommended) ⭐

This is the **recommended approach** for frames that need clear visual identification with orientable x, y, z axes.

### Publish Frame Markers

1. **Define frames in YAML** (see Method 1 above):
   ```bash
   # Edit za6_moveit_config/config/user_frames.yaml
   ```

2. **Publish frame markers:**
   ```bash
   # Make sure MoveIt is running
   ros2 launch za6_moveit_config teleop_hardware.launch.py use_rviz:=true ...
   
   # In another terminal:
   ros2 run za6_moveit_config publish_frame_markers.py
   ```

   The script will:
   - Read frames from `user_frames.yaml` (supports both poses and joint states!)
   - For frames with `joint_state`: Compute forward kinematics to get pose
   - For frames with `pose`: Use pose directly
   - Publish visualization markers with colored axes (Red=X, Green=Y, Blue=Z)
   - Display frame names as text labels
   - **NOT** create collision objects (planner ignores them)
   
   **Note:** For joint-state frames, the script uses MoveIt's forward kinematics service.
   Make sure move_group is running.

3. **View markers in RViz:**
   - Add "MarkerArray" display
   - Subscribe to topic: `/user_frames`
   - You'll see colored axes for each frame!

### Option B: Manual in RViz (Warehouse Storage)

1. **Launch with warehouse enabled:**
   ```bash
   ros2 launch za6_moveit_config teleop_hardware.launch.py db:=true use_rviz:=true ...
   ```

2. **In RViz Motion Planning Plugin:**
   - Go to "Scene Robot" tab
   - Click "Add" → "Box" (or other shape)
   - Position the box at your frame location
   - Set the frame ID as the name
   - Go to "Planning" tab → Click "Save Scene"
   - Enter a name (e.g., "user_frames")
   - Click "Save"
   - Frames persist across restarts!

3. **Load saved scene:**
   - In RViz Motion Planning plugin
   - Go to "Planning" tab → Click "Load Scene"
   - Select your saved scene
   - Frames are restored!

## Method 3: Define in RViz (Temporary)

1. Launch RViz with MoveIt:
   ```bash
   ros2 launch za6_moveit_config teleop_hardware.launch.py use_rviz:=true ...
   ```

2. In RViz:
   - Use "Add" → "Axes" to visualize frames
   - Use "Add" → "Marker" for frame visualization
   - Note: These are visual-only and not part of TF tree

## Method 4: Static Transform Publisher (Command Line)

For quick testing:

```bash
# Publish a static transform
# Syntax: x y z qx qy qz qw parent_frame child_frame
ros2 run tf2_ros static_transform_publisher \
  0.5 0.0 0.75 \
  0 0 0 1 \
  world my_frame
```

## Method 5: URDF/Xacro (Permanent Frames)

For frames that should always exist, add to URDF/Xacro:

Edit `za6_description/urdf/za6.xacro` or create a new xacro file:

```xml
<link name="table_frame"/>
<joint name="table_frame_joint" type="fixed">
  <parent link="world"/>
  <child link="table_frame"/>
  <origin xyz="0.5 0.0 0.75" rpy="0 0 0"/>
</joint>
```

## Usage in Planning

Once frames are defined, you can use them in:

1. **Waypoints:** Reference frames in waypoint definitions
2. **MoveIt Planning:** Use frame names in pose goals
3. **RViz:** Select frame as reference frame for planning
4. **Services/Actions:** Specify frame_id in pose messages

## Verifying Frames

Check if frames are published:

```bash
# List all frames
ros2 run tf2_ros tf2_echo world table_frame

# View TF tree
ros2 run tf2_tools view_frames
# Opens frames.pdf showing the TF tree

# In RViz:
# - Set "Fixed Frame" to "world"
# - Add "TF" display to see all frames
```

## Example: Using Frames in Waypoints

Once frames are defined, reference them in waypoints:

```yaml
- name: Approach Table
  description: 'Move to approach position above table'
  favorite: true
  joint_state:
    # ... joint positions ...
  # Or use pose relative to table_frame:
  pose:
    frame_id: table_frame
    position: [0.0, 0.0, 0.2]  # 20cm above table
    orientation: [0, 0, 0, 1]
```

## Files Created

1. `za6_moveit_config/config/user_frames.yaml` - Frame definitions
2. `za6_moveit_config/launch/user_frames.launch.py` - Launch file to publish static transforms (pose-based frames only)
3. `za6_moveit_config/scripts/publish_frame_markers.py` - Script to publish visual markers with axes (all frame types)
4. `za6_moveit_config/launch/publish_frame_markers.launch.py` - Launch file for marker publisher

## Next Steps

1. Edit `user_frames.yaml` with your custom frames
2. Include `user_frames.launch.py` in your main launch file
3. Rebuild: `colcon build --packages-select za6_moveit_config`
4. Launch and verify frames appear in TF tree

