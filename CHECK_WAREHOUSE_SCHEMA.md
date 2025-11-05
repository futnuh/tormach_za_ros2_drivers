# Check Warehouse Database Schema

## First Step: Inspect Table Structure

Before querying, always check the schema to see what columns exist:

```bash
# Check all table schemas
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".schema"

# Check specific table schema
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".schema \"T_moveit_robot_states@robot_states\""

# Check planning scenes table
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".schema \"T_moveit_planning_scenes@planning_scene\""
```

## List All Tables

```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".tables"
```

## Check Column Names

Once you know the schema, you can query correctly. For example:

```bash
# Interactive mode - check schema first
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite

# Then in sqlite3:
.schema "T_moveit_robot_states@robot_states"
.schema "T_moveit_planning_scenes@planning_scene"
.quit
```

## Common Warehouse Table Structure

The warehouse tables may have different column names depending on the warehouse_ros version. Common columns include:
- `id` - Primary key
- `name` - State/scene name
- `robot` - Robot name
- `state` - Robot state data (blob)
- `scene` - Planning scene data (blob)

But always check the schema first to see the actual structure!

