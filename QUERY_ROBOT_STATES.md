# Querying Robot States from Warehouse Database

## Table Structure

The `T_moveit_robot_states@robot_states` table has these columns:
- `Data` - BLOB (robot state data)
- `M_id` - INTEGER PRIMARY KEY
- `M_creation_time` - INTEGER
- `M_robot_id` - BLOB (robot identifier)
- `M_state_id` - BLOB (state identifier/name)

## Check WarehouseIndex for Names

The warehouse uses a `WarehouseIndex` table to store names. Check it:

```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".schema WarehouseIndex"
```

## Quick Commands

### List All Robot State IDs
```bash
# Show all state IDs (these are BLOBs, may need decoding)
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT M_id, M_state_id, M_robot_id FROM \"T_moveit_robot_states@robot_states\";"
```

### Count Robot States
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT COUNT(*) FROM \"T_moveit_robot_states@robot_states\";"
```

### Show All Robot States (with IDs)
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite -header -column "SELECT M_id, M_creation_time, M_robot_id, M_state_id FROM \"T_moveit_robot_states@robot_states\";"
```

### Readable Format with Headers
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite -header -column "SELECT name, robot FROM \"T_moveit_robot_states@robot_states\";"
```

### Count Robot States
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT COUNT(*) FROM \"T_moveit_robot_states@robot_states\";"
```

### Show Specific Robot State (by name)
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT * FROM \"T_moveit_robot_states@robot_states\" WHERE name='state_name';"
```

### Show All Robot States (all columns)
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT * FROM \"T_moveit_robot_states@robot_states\";"
```

### Show Robot States for Specific Robot
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT name FROM \"T_moveit_robot_states@robot_states\" WHERE robot='za6';"
```

## Interactive Mode

```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite
```

Then:
```sql
.headers on
.mode column

-- List all robot states
SELECT name, robot FROM "T_moveit_robot_states@robot_states";

-- Show specific state
SELECT * FROM "T_moveit_robot_states@robot_states" WHERE name='my_state';

-- Count states
SELECT COUNT(*) FROM "T_moveit_robot_states@robot_states";

.quit
```

## Most Useful Command

For a quick overview:
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite -header -column "SELECT name, robot FROM \"T_moveit_robot_states@robot_states\" ORDER BY name;"
```

## Note on Table Names

The warehouse uses table names with "@" symbols (e.g., `T_moveit_robot_states@robot_states`). 
These need to be quoted in SQL queries, hence the double quotes and escaped quotes in bash commands.

