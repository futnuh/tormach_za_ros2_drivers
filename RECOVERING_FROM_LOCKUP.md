# Recovering From Workspace Lockups

When the host or the `ros2-devel` container locks up during a `colcon` build (typically because of resource exhaustion), the machine must be rebooted. Rebooting resets the container’s filesystem and removes several ROS dependencies, so subsequent builds fail with missing-package errors until those dependencies are reinstalled.

After restarting the `ros2-devel` container, run the following command inside it to restore everything required by `moveit_ros_visualization`:

```
sudo apt-get update
sudo apt-get install -y \
  ros-humble-geometric-shapes \
  ros-humble-srdfdom \
  ros-humble-object-recognition-msgs \
  ros-humble-octomap-msgs \
  ros-humble-ruckig \
  ros-humble-octomap \
  libfcl-dev \
  liboctomap-dev
```

Once the packages are back in place, re-source `/opt/ros/humble/setup.bash` (and the workspace overlay if needed) before rerunning `colcon`. To prevent repeat lockups, keep build parallelism low (e.g., `--executor sequential --parallel-workers 1`) and consider baking these dependency installs into the Docker image so the environment comes up ready without manual recovery steps.


