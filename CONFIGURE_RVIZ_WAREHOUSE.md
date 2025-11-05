# Configure RViz Warehouse Connection on Startup

## Method 1: Manual Configuration (Recommended)

1. **Launch RViz with warehouse enabled:**
   ```bash
   ros2 launch za6_moveit_config teleop_hardware.launch.py \
     use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
     use_rviz:=true \
     servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
     db:=true
   ```

2. **In RViz Motion Planning Plugin:**
   - Go to "Context" tab
   - Set "Warehouse Host" to: `/home/pathpilot/.ros/warehouse/moveit_warehouse.sqlite`
   - Set "Warehouse Port" to: `0`
   - Click "Connect" button
   - Verify connection is successful

3. **Save RViz Config:**
   - File → Save Config As...
   - Save to: `za6_moveit_config/config/moveit.rviz` (overwrite existing)
   - Or save to a new file and update launch file to use it

4. **The warehouse connection will now auto-connect on startup**

## Method 2: Programmatic Configuration

The warehouse connection settings are stored in the RViz config file. However, the Motion Planning plugin's warehouse connection settings are stored in the plugin's internal state, which is encoded in the RViz config.

The easiest way is to:
1. Configure once manually in RViz
2. Save the config
3. Future launches will use the saved settings

## Method 3: Check Current Config

The warehouse parameters are already being passed to RViz via launch file:
- `warehouse_plugin`: `warehouse_ros_sqlite::DatabaseConnection`
- `warehouse_host`: `/home/pathpilot/.ros/warehouse/moveit_warehouse.sqlite`
- `warehouse_port`: `0`

But the Motion Planning plugin needs these settings in its own config section.

## Verification

After configuring and saving:
1. Restart RViz
2. Check "Context" tab in Motion Planning plugin
3. Warehouse connection should be established automatically
4. "Load Scene" dropdown should show available scenes

## Troubleshooting

If auto-connection doesn't work:
1. Make sure warehouse is running (`db:=true`)
2. Check that the config file was saved correctly
3. Verify warehouse host path is correct
4. Manually click "Connect" once, then save config again

