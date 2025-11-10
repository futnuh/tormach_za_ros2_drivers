# Warehouse Database Query Summary

## Key Finding

The warehouse_ros_sqlite stores names as **BLOBs**, not text columns. This means:
- Direct SQL queries won't give you readable names
- Use ROS2 services for readable names
- SQL is useful for counting, checking existence, and raw data access

## Quick Reference

### Count Robot States
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT COUNT(*) FROM \"T_moveit_robot_states@robot_states\";"
```

### Count Planning Scenes
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT COUNT(*) FROM \"T_moveit_planning_scenes@planning_scene\";"
```

### Check if Scene Exists (by checking count)
```bash
# Check if "user_frames" scene exists (if you know it was saved)
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT COUNT(*) FROM \"T_moveit_planning_scenes@planning_scene\";"
```

### List All Tables
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".tables"
```

### Show Table Schemas
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".schema"
```

## Recommended: Use ROS2 Services for Readable Names

### List Robot States (with readable names)
```bash
ros2 service call /list_robot_states std_srvs/srv/Empty
```

### List Planning Scenes (via RViz)
- Use RViz Motion Planning plugin
- Go to "Planning" tab
- Click "Load Scene" dropdown
- See all saved scene names

### Get Robot State
```bash
ros2 service call /get_robot_state moveit_msgs/srv/GetRobotStateFromWarehouse "{name: 'state_name', robot: 'za6'}"
```

## Why Use Services Instead of SQL?

1. **Readable Names**: Services decode BLOBs to readable text
2. **Type Safety**: Services use proper ROS2 message types
3. **Easier**: No need to decode BLOBs manually
4. **Standard**: This is how warehouse_ros is designed to be used

## SQL Use Cases

SQL is still useful for:
- ✅ Counting records
- ✅ Checking if data exists
- ✅ Database maintenance
- ✅ Backup/restore operations
- ✅ Raw data inspection

But for **readable names**, use ROS2 services!

