# ROS2 MoveIt2 Warehouse Support Guide

## Current State

The warehouse infrastructure is **already partially set up** in your system:

### ✅ What's Already in Place:

1. **Dependencies Installed:**
   - `warehouse_ros_sqlite` - SQLite backend for warehouse
   - `moveit_ros_warehouse` - MoveIt warehouse ROS interface
   - Both are listed in `za6_moveit_config/package.xml`

2. **Launch Files Configured:**
   - `za6_moveit_config/launch/warehouse_db.launch.py` - Warehouse launch file exists
   - `za6_bringup/launch/bringup.launch` - Has `db` parameter (line 257-265)
   - `za6_moveit_config/launch/demo.launch.py` - Has `db` parameter (line 137-142, 190-198)
   - `za6_moveit_config/launch/teleop_hardware.launch.py` - Has `db` parameter (passes through to bringup)

3. **Integration Points:**
   - Warehouse can be enabled via `db:=true` launch argument
   - Currently disabled by default (`db:=false`)

## What Warehouse Stores

MoveIt2 Warehouse (with SQLite) can persistently store:

1. **Motion Plans** - Saved trajectories/plans
2. **Planning Scenes** - Complete planning scene states with objects
3. **Robot States** - Named robot configurations
4. **Constraints** - Planning constraints
5. **State Constraints** - State-specific constraints

**Note:** Waypoints are currently stored in YAML files (`config/waypoints.yaml`) and loaded by MoveIt Studio. The warehouse doesn't directly replace this, but you can:
- Store robot states that correspond to waypoints
- Use warehouse to store planning scenes and motion plans

## Steps to Enable and Use Warehouse

### Step 1: Enable Warehouse in Launch Files

The warehouse is already configured but disabled by default. You have two options:

#### Option A: Enable by Default (Recommended for Development)

Modify `za6_bringup/launch/bringup.launch` to change the default:

```xml
<arg
    name="db"
    default="true"    <!-- Change from "false" to "true" -->
    description="Start database; default True"
    />
```

#### Option B: Enable on Launch Command Line

Keep default as `false` and enable when needed:

```bash
# For standard bringup
ros2 launch za6_bringup bringup.launch db:=true

# For teleop hardware (gamepad teleoperation)
ros2 launch za6_moveit_config teleop_hardware.launch.py db:=true \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml

# For demo (simulation)
ros2 launch za6_moveit_config demo.launch.py db:=true
```

### Step 2: Configure Database Location (Optional)

The warehouse database location can be configured. Check the `generate_warehouse_db_launch` function from `moveit_configs_utils.launches`. By default, SQLite databases are typically stored in:
- `~/.ros/warehouse/` or
- A location specified by `warehouse_plugin` parameter

You may want to customize `warehouse_db.launch.py` to specify a custom database path:

```python
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_warehouse_db_launch
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    moveit_config = MoveItConfigsBuilder(
        "za6", package_name="za6_moveit_config"
    ).to_moveit_configs()
    
    # Customize warehouse launch with database path
    warehouse_launch = generate_warehouse_db_launch(moveit_config)
    
    # You can add custom database path configuration here
    # This would require modifying how the warehouse connection is set up
    
    return warehouse_launch
```

### Step 3: Interact with Warehouse

#### Using RViz Motion Planning Plugin

1. Launch with warehouse enabled:
   ```bash
   ros2 launch za6_bringup bringup.launch db:=true
   ```

2. In RViz Motion Planning plugin:
   - Go to "Contexts" tab
   - You can save/load:
     - **Planning Scenes** - Complete scenes with objects
     - **Motion Plans** - Saved trajectories
     - **Robot States** - Named joint configurations

#### Using ROS2 Services

The warehouse provides services for saving/loading data:

**Save Robot State:**
```bash
ros2 service call /save_robot_state moveit_msgs/srv/SaveRobotStateToWarehouse \
  "{name: 'my_waypoint', robot: 'za6', state: {...}}"
```

**List Robot States:**
```bash
ros2 service call /list_robot_states std_srvs/srv/Empty
```

**Save Planning Scene:**
```bash
ros2 service call /save_scene moveit_msgs/srv/SaveScene \
  "{filename: 'my_scene.scene'}"
```

### Step 4: Integrate Waypoints with Warehouse (Advanced)

Currently, waypoints are YAML-based. To migrate or integrate with warehouse:

1. **Create a script** to convert YAML waypoints to warehouse robot states
2. **Modify waypoint loading** to query warehouse when available
3. **Create a service/action** to save current robot state as a waypoint to warehouse

Example approach:
- Create a new package `za6_warehouse_tools` with scripts to:
  - Import YAML waypoints into warehouse
  - Export warehouse states to YAML
  - Provide ROS2 services to manage waypoints in warehouse

### Step 5: Database Management

**View Database:**
The SQLite database file will be created automatically. Find it in the default location or as configured.

**Backup Database:**
```bash
cp ~/.ros/warehouse/moveit_warehouse.sqlite ~/backup_moveit_warehouse.sqlite
```

**Clear Database:**
Stop the warehouse and delete the database file, or use warehouse services to delete specific entries.

## Testing Warehouse

1. **Launch with warehouse:**
   ```bash
   source install/setup.bash
   ros2 launch za6_bringup bringup.launch db:=true
   
   # Or for teleop:
   ros2 launch za6_moveit_config teleop_hardware.launch.py db:=true \
     use_fake_hardware:=false sim_mode:=false use_sim_time:=false use_rviz:=true \
     servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml
   ```

2. **Database Initialization:**
   - On first launch, the warehouse will create the SQLite database at `~/.ros/warehouse/moveit_warehouse.sqlite`
   - You may see a schema error on first connection - this is normal. The schema will be created when you first save data.

3. **In RViz:**
   - Move robot to a desired pose
   - Go to Motion Planning plugin → Planning Request tab
   - Click "Save" to save current state
   - Name the state (e.g., "my_test_waypoint")
   - The first save will initialize the database schema
   - Restart and verify state persists

4. **Verify Warehouse is Running:**
   ```bash
   # Check if warehouse node is running
   ros2 node list | grep warehouse
   
   # Check warehouse services
   ros2 service list | grep warehouse
   ```

5. **Using Command Line:**
   ```bash
   # Get current robot state
   ros2 topic echo /joint_states --once
   
   # Save to warehouse (requires custom service call or script)
   ```

## Next Steps / Recommendations

1. **Enable warehouse by default** for development/testing (Option A above)
2. **Create utility scripts** in `za6_tools` or new package to:
   - Migrate YAML waypoints to warehouse
   - Provide CLI tools to manage warehouse entries
   - Create ROS2 services/actions for waypoint management
3. **Document waypoint workflow**: Decide whether to:
   - Keep YAML for initial/default waypoints
   - Use warehouse for user-created waypoints
   - Fully migrate to warehouse-only
4. **Add warehouse configuration** to config files for:
   - Database path
   - Auto-load initial states/scenes
   - Warehouse backup strategy

## References

- [MoveIt2 Warehouse Tutorial](https://moveit.picknik.ai/main/doc/tutorials/persistent_scenes_states/persistent_scenes_states_tutorial.html)
- [warehouse_ros_sqlite GitHub](https://github.com/ros-planning/warehouse_ros_sqlite)
- [moveit_ros_warehouse Documentation](https://moveit.picknik.ai/main/doc/concepts/warehouse.html)

