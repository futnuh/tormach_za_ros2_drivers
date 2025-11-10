# Fix Missing 'joy' Package Error

## Problem

When launching, you see:
```
[ERROR] [launch]: Caught exception in launch (see debug for traceback): "package 'joy' not found"
```

## Solution

The `joy` package is a standard ROS2 package that provides joystick/gamepad support. It needs to be installed.

### Install joy Package

**Inside docker container:**
```bash
sudo apt-get update
sudo apt-get install ros-humble-joy
```

### Verify Installation

```bash
# Check if package is installed
ros2 pkg list | grep joy

# Check if executable exists
ros2 pkg executables joy

# Should show:
# joy joy_node
```

### Alternative: Check if Already Installed

Sometimes the package is installed but not in the workspace path. Check:

```bash
# Check if joy_node executable exists
which joy_node

# Or check system-wide
ros2 run joy joy_node --help
```

## After Installing

Once installed, your launch command should work:

```bash
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
  db:=true
```

## Note

If you're in a docker container, you may need to install the package inside the container. The package is typically pre-installed in ROS2 Docker images, but if it's missing, install it as shown above.

