# Development Notes

## Critical: ROS 2 Commands Must Run in Docker Container

**IMPORTANT**: All ROS 2 commands (`ros2`, `colcon`, etc.) **MUST** be executed inside the Docker container `ros2-devel`. The ROS 2 environment is not available in the host shell.

### Quick Reference

```bash
# Enter the container interactively
docker exec -it ros2-devel bash

# Run a single ROS 2 command
docker exec ros2-devel ros2 <command>

# Run with workspace directory
docker exec -w /home/pathpilot/Projects/za6_workspace ros2-devel ros2 <command>
```

### Helper Script

A helper script `ros2-in-docker.sh` is available in the workspace root to simplify this:

```bash
# Instead of: ros2 topic list
./ros2-in-docker.sh topic list

# Instead of: ros2 launch za6_moveit_config teleop_hardware.launch.py
./ros2-in-docker.sh launch za6_moveit_config teleop_hardware.launch.py
```

### Why This Matters

- The ROS 2 installation, workspace, and all dependencies are inside the Docker container
- The host system does not have ROS 2 installed
- Attempting to run `ros2` commands in the host shell will always fail with "command not found"
- All development, testing, and debugging must happen inside the container

### Common Workflow

1. **Launch the stack** (from host or container):
   ```bash
   docker exec -w /home/pathpilot/Projects/za6_workspace ros2-devel \
     ros2 launch za6_moveit_config teleop_hardware.launch.py ...
   ```

2. **Run diagnostic commands** (from host):
   ```bash
   docker exec ros2-devel ros2 topic list
   docker exec ros2-devel ros2 topic echo /joint_states
   ```

3. **Interactive debugging** (enter container):
   ```bash
   docker exec -it ros2-devel bash
   cd /home/pathpilot/Projects/za6_workspace
   source install/setup.bash
   ros2 run <package> <executable>
   ```

## Other Development Notes

### Workspace Location

The workspace is mounted at `/home/pathpilot/Projects/za6_workspace` inside the container, which maps to the host workspace directory.

### Building

All builds must happen inside the container:
```bash
docker exec -w /home/pathpilot/Projects/za6_workspace ros2-devel \
  colcon build --symlink-install ...
```

