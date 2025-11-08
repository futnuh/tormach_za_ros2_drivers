# Docker Image Dependency Fixes

The `ros2-devel` container lost several runtime libraries after reboot, causing repeated build failures. To make the image self-contained, update the Docker build scripts (located under `devel_scripts/docker/`) so the problematic packages are installed during image creation instead of manually inside a running container.

## Required Package Additions

Add the following Debian packages to the MoveIt dependency install script (`ros_custom/install_moveit2_deps.sh`) or another appropriate build stage:

- `ros-humble-geometric-shapes`
- `ros-humble-srdfdom`
- `ros-humble-object-recognition-msgs`
- `ros-humble-octomap-msgs`
- `ros-humble-ruckig`
- `ros-humble-octomap`
- `ros-humble-launch-param-builder`
- `ros-humble-ompl`
- `libfcl-dev`
- `liboctomap-dev`

These cover the missing libraries that blocked the `moveit_ros_visualization` build (`geometric_shapes`, `srdfdom`, `fcl`, `object_recognition_msgs`, `octomap_msgs`, `ruckig`, `octomap`, `launch_param_builder`, `ompl`) and the patches installed manually during recovery.

## Implementation Notes

- The current Docker scripts already install many MoveIt prerequisites; ensure the list above is present and kept in sync with any new dependencies introduced by MoveIt or the ZA6 packages.
- After editing the scripts, rebuild the container image (e.g., rerun the existing build pipeline) so the new packages bake into the published image. Existing containers must be recreated from the updated image to pick up the changes.
- Document the rebuild step alongside other recovery instructions so future lockups do not require manual package installs.

By installing these packages during the Docker build, the runtime container will retain the required dependencies across restarts and avoid repeated manual intervention.


