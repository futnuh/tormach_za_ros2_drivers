# Using Patched moveit_servo

## Overview

The teleop system uses a patched version of `moveit_servo` built from `/tmp/moveit2_za6_ws`. This workspace needs to be built and sourced for the patched version to be available.

## Check if Patched Version Exists

**Inside docker container:**
```bash
# Check if executable exists
ls -lh /tmp/moveit2_za6_ws/install/moveit_servo/lib/moveit_servo/servo_node_main

# Check if workspace is built
ls -d /tmp/moveit2_za6_ws/install/moveit_servo 2>/dev/null && echo "Workspace exists" || echo "Workspace not found"
```

## Rebuild Patched moveit_servo

If the patched version doesn't exist or needs to be rebuilt:

**Inside docker container:**
```bash
# Navigate to workspace
cd /tmp/moveit2_za6_ws

# Create symlink to source (if needed)
ln -sf /home/pathpilot/Temp/moveit2/moveit_ros src

# Build moveit_servo
colcon build --packages-select moveit_servo --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# Source the workspace
source install/setup.bash
```

Or use the provided script:
```bash
cd /home/pathpilot/Temp/tormach_za_ros2_drivers
bash REBUILD_SERVO.sh
```

## Launch File Configuration

The launch file (`teleop_hardware.launch.py`) has been updated to:
1. Check if patched version exists at `/tmp/moveit2_za6_ws/install/moveit_servo/lib/moveit_servo/servo_node_main`
2. Use direct path to patched executable if available
3. Fall back to package lookup if patched version not found

## Source Workspace Before Launching

**Important:** Before launching, you may need to source the patched workspace:

```bash
# Source patched moveit_servo workspace
source /tmp/moveit2_za6_ws/install/setup.bash

# Then launch
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

## Alternative: Auto-Source in Launch File

The launch file could be modified to automatically source the workspace, but it's simpler to source it manually before launching.

## Verification

After rebuilding and sourcing:
```bash
# Check executable exists
ls -lh /tmp/moveit2_za6_ws/install/moveit_servo/lib/moveit_servo/servo_node_main

# Check if it's executable
file /tmp/moveit2_za6_ws/install/moveit_servo/lib/moveit_servo/servo_node_main
```

