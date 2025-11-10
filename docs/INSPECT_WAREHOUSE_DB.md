# Inspecting Warehouse SQLite Database

## Using sqlite3 Command-Line Tool

The `sqlite3` command-line tool is typically pre-installed on Linux systems. Use it to inspect the warehouse database.

## Basic Commands

### Open Database
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite
```

### List All Tables
```sql
.tables
```

### Show Schema for All Tables
```sql
.schema
```

### Show Schema for Specific Table
```sql
.schema <table_name>
```

### List Scenes
```sql
SELECT * FROM "T_moveit_planning_scenes@planning_scene";
```

### Show Scene Names
```sql
SELECT name FROM "T_moveit_planning_scenes@planning_scene";
```

### Count Records
```sql
SELECT COUNT(*) FROM "T_moveit_planning_scenes@planning_scene";
SELECT COUNT(*) FROM "T_moveit_robot_states@robot_states";
```

### Exit sqlite3
```sql
.quit
```

## One-Line Commands (Without Interactive Shell)

### List All Tables
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".tables"
```

### Show Schema
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite ".schema"
```

### List Scene Names
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT name FROM \"T_moveit_planning_scenes@planning_scene\";"
```

### Count All Scenes
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT COUNT(*) FROM \"T_moveit_planning_scenes@planning_scene\";"
```

### Show All Scene Data
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT * FROM \"T_moveit_planning_scenes@planning_scene\";"
```

### Show Scene Info (Readable Format)
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite -header -column "SELECT name, robot FROM \"T_moveit_planning_scenes@planning_scene\";"
```

## Useful Queries

### Check if "user_frames" Scene Exists
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "SELECT name FROM \"T_moveit_planning_scenes@planning_scene\" WHERE name='user_frames';"
```

### Show Database Info (Table Names and Row Counts)
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite "
SELECT 
  name as table_name,
  (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as row_count
FROM sqlite_master m 
WHERE type='table';
"
```

### List All Robot States
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite -header -column "SELECT name, robot FROM \"T_moveit_robot_states@robot_states\";"
```

## Interactive Mode

For interactive exploration:
```bash
sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite
```

Then use SQL commands:
```sql
-- Set output format
.mode column
.headers on

-- Show all tables
.tables

-- Show scene names
SELECT name FROM "T_moveit_planning_scenes@planning_scene";

-- Show specific scene
SELECT * FROM "T_moveit_planning_scenes@planning_scene" WHERE name='user_frames';

-- Exit
.quit
```

## Alternative: Using Python

If sqlite3 isn't available, use Python:
```bash
python3 -c "
import sqlite3
import os
conn = sqlite3.connect(os.path.expanduser('~/.ros/warehouse/moveit_warehouse.sqlite'))
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print('Tables:', [row[0] for row in cursor.fetchall()])
cursor.execute('SELECT name FROM \"T_moveit_planning_scenes@planning_scene\"')
print('Scenes:', [row[0] for row in cursor.fetchall()])
cursor.execute('SELECT name FROM \"T_moveit_robot_states@robot_states\"')
print('Robot States:', [row[0] for row in cursor.fetchall()])
conn.close()
"
```

## Installation (If Not Available)

If `sqlite3` is not installed:
```bash
# Ubuntu/Debian
sudo apt-get install sqlite3

# Or use Python (usually pre-installed)
python3 -m sqlite3 ~/.ros/warehouse/moveit_warehouse.sqlite
```

