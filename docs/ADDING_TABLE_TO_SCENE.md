# Adding Robot Table to MoveIt Planning Scene

This document describes the implementation of adding a robot table (collision and visualization models) to the MoveIt planning scene and RViz display.

## Overview

The robot table is added to the planning scene using two separate 3D models:
- **Collision Model**: Low-poly mesh for efficient collision checking in MoveIt
- **Visualization Model**: High-resolution mesh for realistic display in RViz

Both models are automatically loaded when the robot stack launches, ensuring the table is always present for planning and visualization.

## Model Files

The table models now live inside the company-specific `za6_moveit_config/meshes/edm/` folder:
- `za6_moveit_config/meshes/edm/RobotTableCollisionVolume.obj` - Low-poly collision mesh
- `za6_moveit_config/meshes/edm/RobotTableVisualizationModel.obj` - High-resolution visualization mesh

Both models are pre-positioned and oriented in world space, so no manual transforms are needed during loading.

## Implementation

### Script: `add_table_to_scene.py`

**Location**: `za6_moveit_config/scripts/add_table_to_scene.py`

**Purpose**: Loads OBJ files and publishes them to MoveIt planning scene and RViz visualization.

**Key Features**:
1. **OBJ File Parsing**: Parses OBJ format files to extract vertices and triangles
2. **Collision Object**: Publishes `moveit_msgs/CollisionObject` to `/planning_scene` for MoveIt collision checking
3. **Visualization Marker**: Publishes `visualization_msgs/Marker` to `/visualization_marker_array` for RViz display
4. **Transparent Collision**: Makes collision object invisible (alpha=0) so visualization model shows through
5. **Position Adjustment**: Shifts collision object down by 0.001m in z-axis for fine-tuning

**Message Types**:
- **Collision Object**: `moveit_msgs/msg/CollisionObject` → `/planning_scene`
  - Used by MoveIt for collision checking during motion planning
  - Made transparent so it doesn't obscure the visualization model
  
- **Visualization Marker**: `visualization_msgs/msg/Marker` → `/visualization_marker_array`
  - Used by RViz for display only (not used for collision checking)
  - High-resolution model for realistic appearance

**Argument Handling**:
The script properly filters out ROS 2 launch arguments (`--ros-args`, `-r`, `__node:=...`, `--params-file`, etc.) to allow optional user-provided OBJ file paths while maintaining compatibility with ROS 2 launch system.

### Launch File Integration

**Location**: `za6_moveit_config/launch/teleop_hardware.launch.py`

The script is integrated using a `TimerAction` with a 5-second delay to ensure MoveIt and RViz are fully initialized before adding the table:

```python
# 8) Add table to planning scene (after system is up)
# Delay by 5 seconds to ensure MoveIt and RViz are ready
add_table_node = TimerAction(
    period=5.0,
    actions=[
        Node(
            package="za6_moveit_config",
            executable="add_table_to_scene.py",
            name="add_table_to_scene",
            parameters=[
                {"use_sim_time": use_sim_time},
            ],
            output="screen",
        )
    ],
)
```

**Why the delay?**
- MoveIt's planning scene monitor needs time to initialize
- RViz needs time to start and subscribe to topics
- Ensures the table is added after all subscribers are ready

### RViz Configuration

**Location**: `za6_moveit_config/config/moveit.rviz`

The RViz configuration includes a `MarkerArray` display to show the visualization model:

```yaml
- Class: rviz_default_plugins/MarkerArray
  Enabled: true
  Name: MarkerArray
  Topic:
    Value: /visualization_marker_array
  Value: true
```

**Key Points**:
- The `MarkerArray` display subscribes to `/visualization_marker_array`
- This is separate from the collision object, which appears in the "Scene Objects" pane
- The visualization marker is display-only and does not affect collision checking

## Workflow

1. **Launch**: When `teleop_hardware.launch.py` is launched, the `add_table_to_scene.py` script is scheduled to run after 5 seconds
2. **Initialization**: The script waits for at least one subscriber to `/planning_scene` (MoveIt planning scene monitor)
3. **Loading**: Both OBJ files are loaded and parsed
4. **Publishing**:
   - Collision object is published to `/planning_scene` (transparent, for collision checking)
   - Visualization marker is published to `/visualization_marker_array` (visible, for display)
5. **Result**: The table appears in RViz and is used by MoveIt for collision checking

## Troubleshooting

### Table Not Appearing in RViz

**Symptoms**: Table models don't appear in RViz after launch

**Possible Causes**:
1. **OBJ files not found**: Check that `RobotTableCollisionVolume.obj` and `RobotTableVisualizationModel.obj` exist in workspace root
2. **Script not running**: Check launch logs for `add_table_to_scene` node errors
3. **MarkerArray display not enabled**: Verify `MarkerArray` display is enabled in RViz config
4. **Topic mismatch**: Ensure MarkerArray display subscribes to `/visualization_marker_array`

**Diagnosis**:
```bash
# Check if script is running
ros2 node list | grep add_table

# Check if topics are being published
ros2 topic list | grep -E "(planning_scene|visualization_marker_array)"

# Check script output
ros2 topic echo /rosout --filter "name=='add_table_to_scene'"
```

### Collision Object Not Working

**Symptoms**: Robot plans through the table or table doesn't block motion

**Possible Causes**:
1. **Collision object not published**: Check `/planning_scene` topic for `robot_table` collision object
2. **Planning scene not updated**: Verify MoveIt planning scene monitor is subscribed to `/planning_scene`
3. **Object ID mismatch**: Ensure collision object ID is `robot_table`

**Diagnosis**:
```bash
# Check planning scene for collision objects
ros2 topic echo /planning_scene --once | grep -A 10 "robot_table"

# Check MoveIt planning scene monitor
ros2 topic info /monitored_planning_scene
```

### Script Crashes on Launch

**Symptoms**: `add_table_to_scene.py` exits with error code 1

**Common Errors**:
- **"Collision OBJ file not found: --ros-args"**: Fixed by filtering ROS 2 arguments (see implementation)
- **"No vertices found in OBJ file"**: OBJ file is empty or malformed
- **"Planning scene subscriber not detected"**: MoveIt not fully initialized (increase delay or check MoveIt startup)

**Solution**: Check script logs in launch output for specific error messages.

## Manual Testing

The script can be run manually for testing:

```bash
# From workspace root
ros2 run za6_moveit_config add_table_to_scene.py

# Or with custom OBJ file path
ros2 run za6_moveit_config add_table_to_scene.py /path/to/custom_table.obj
```

**Note**: When run manually, the script will:
- Wait up to 15 seconds for planning scene subscribers
- Publish both collision and visualization models
- Exit after publishing (one-shot execution)

## Technical Details

### Collision Object Properties

- **ID**: `robot_table`
- **Operation**: `ADD` (adds to planning scene)
- **Frame**: `world`
- **Type**: `MESH` (from OBJ file)
- **Color**: Transparent (alpha=0) to allow visualization model to show through
- **Position**: Shifted down 0.001m in z-axis for fine-tuning

### Visualization Marker Properties

- **Type**: `MESH_RESOURCE`
- **Namespace**: `robot_table_visual_ns`
- **ID**: `0`
- **Frame**: `world`
- **Mesh Resource**: File path to `RobotTableVisualizationModel.obj`
- **Use Embedded Materials**: `true` (uses MTL file if present)
- **Lifetime**: `0` (permanent)

### OBJ File Format Support

The script supports standard OBJ format:
- **Vertices**: `v x y z` lines
- **Faces**: `f v1 v2 v3` lines (triangular faces)
- **Comments**: Lines starting with `#` are ignored
- **Texture/Normal indices**: Handled by taking first number (vertex index)

**Limitations**:
- Only triangular faces are supported (quads are not triangulated)
- Material files (MTL) are not parsed (but can be used by RViz if embedded)
- Negative vertex indices are supported (relative indexing)

## Future Improvements

Potential enhancements:
1. **Dynamic table positioning**: Add ROS 2 parameters for table position/orientation
2. **Multiple tables**: Support loading multiple table models
3. **Table removal**: Add service to remove table from scene
4. **Table state persistence**: Save table configuration to warehouse
5. **MTL file parsing**: Parse material files for better visualization
6. **Collision model simplification**: Automatic mesh decimation for collision models

## Related Files

- **Script**: `za6_moveit_config/scripts/add_table_to_scene.py`
- **Launch Integration**: `za6_moveit_config/launch/teleop_hardware.launch.py`
- **RViz Config**: `za6_moveit_config/config/moveit.rviz`
- **CMakeLists**: `za6_moveit_config/CMakeLists.txt` (installs script as executable)
- **Model Files**: Workspace root (`RobotTableCollisionVolume.obj`, `RobotTableVisualizationModel.obj`)

## References

- [MoveIt Collision Objects Documentation](https://moveit.picknik.ai/main/doc/concepts/collision_detection.html)
- [RViz MarkerArray Display](http://wiki.ros.org/rviz/DisplayTypes/MarkerArray)
- [OBJ File Format Specification](https://en.wikipedia.org/wiki/Wavefront_.obj_file)

