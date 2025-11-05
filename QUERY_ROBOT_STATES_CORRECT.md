# Querying Robot States from Warehouse Database (Correct Structure)

## Table Structure

The `T_moveit_robot_states@robot_states` table has these columns:
- `Data` - BLOB (robot state data)
- `M_id` - INTEGER PRIMARY KEY
- `M_creation_time` - INTEGER (timestamp)
- `M_robot_id` - BLOB (robot identifier)
- `M_state_id` - BLOB (state identifier/name)

**Note:** The warehouse_ros_sqlite stores names/IDs as BLOBs, not text columns. The actual names might be stored in the WarehouseIndex table or encoded in the BLOB fields.

## Check WarehouseIndex Table

The warehouse may use a separate index table for names:

```bash
# Check WarehouseIndex schema
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".schema WarehouseIndex"

# View WarehouseIndex contents
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT * FROM WarehouseIndex;"
```

## Query Robot States

### Count Robot States
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT COUNT(*) FROM \"T_moveit_robot_states@robot_states\";"
```

### Show All Robot States (IDs and Metadata)
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite -header -column "SELECT M_id, M_creation_time FROM \"T_moveit_robot_states@robot_states\";"
```

### Show State IDs (as hex for readability)
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT M_id, hex(M_state_id) as state_id_hex, hex(M_robot_id) as robot_id_hex FROM \"T_moveit_robot_states@robot_states\";"
```

### Show Specific State by ID
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT * FROM \"T_moveit_robot_states@robot_states\" WHERE M_id=1;"
```

## Check WarehouseIndex

The WarehouseIndex table maps table names to message types (not readable names):

```bash
# View index contents
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT * FROM WarehouseIndex;"
```

**Note:** The WarehouseIndex doesn't contain readable state names - it just maps table names to message types. State names are stored as BLOBs in the `M_state_id` field.

## Using ROS2 Services (Recommended)

Since the warehouse stores names as BLOBs, **use ROS2 services** for readable names:

```bash
# List robot states via ROS2 service (returns readable names)
ros2 service call /list_robot_states std_srvs/srv/Empty

# Get specific robot state
ros2 service call /get_robot_state moveit_msgs/srv/GetRobotStateFromWarehouse "{name: 'state_name', robot: 'za6'}"
```

**This is the recommended way** to get readable state names since the database stores them as BLOBs.

## Interactive Exploration

```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite
```

Then:
```sql
.headers on
.mode column

-- Check table structure
.schema "T_moveit_robot_states@robot_states"
.schema WarehouseIndex

-- Count states
SELECT COUNT(*) FROM "T_moveit_robot_states@robot_states";

-- Show state IDs
SELECT M_id, hex(M_state_id) FROM "T_moveit_robot_states@robot_states";

-- Check index
SELECT * FROM WarehouseIndex;

.quit
```

