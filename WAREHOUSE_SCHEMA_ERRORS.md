# Warehouse Schema Errors - Expected on First Use

## Issue: Database Schema Errors in RViz

When you first connect to the warehouse database, you may see errors like:

```
[ERROR] [warehouse_ros_sqlite.query]: Preparing Query failed: no such column: M_planning_scene_id
[ERROR] [warehouse_ros_sqlite.query]: Preparing Query failed: no such column: M_robot_id
```

## Explanation

These errors are **expected and normal** on first use. The warehouse database schema is created **lazily** - meaning the tables and columns are created automatically when the first data is saved.

## Solution

The schema will be created automatically when you:

1. **Save a scene to warehouse** using the store script:
   ```bash
   ros2 run za6_moveit_config store_frames_to_warehouse.py
   ```

2. **Or save a scene from RViz:**
   - In RViz Motion Planning plugin
   - Go to "Planning" tab
   - Click "Save Scene"
   - Enter a name (e.g., "test_scene")
   - Click "Save"

After saving the first scene, the database schema will be fully initialized and the errors will stop appearing.

## Verification

After storing frames, verify the schema was created:

```bash
# Check database exists and has data
ls -lh ~/.ros/warehouse/moveit_warehouse.sqlite

# The database should grow in size after saving
```

## Alternative: Pre-initialize Schema

If you want to avoid the errors entirely, you can pre-initialize the schema by:

1. **Save an empty scene from RViz:**
   - Add Motion Planning plugin
   - Go to "Planning" tab
   - Click "Save Scene" → Name: "init"
   - This creates the schema

2. **Or run the store script** (which will create the schema):
   ```bash
   ros2 run za6_moveit_config store_frames_to_warehouse.py
   ```

## Notes

- The errors are harmless - they just indicate the schema isn't created yet
- Once the schema is created, it persists (database file remains)
- The errors won't appear on subsequent launches
- The schema is specific to the warehouse plugin (SQLite in this case)

