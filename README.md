# `tormach_za_ros2_drivers`

This repository contains the Tormach ZA robot ROS 2 drivers,
including:

- `za6_description`:  URDF and mesh files for the ZA6
- `za6_tools`:  URDF and meshfiles for Tormach robot grippers
- `za6_hardware`:  HAL hardware drivers for the ZA6
- `za6_moveit_config`:  MoveIt configuration
- `za6_bringup`:  Launch files to bring up the robot

It also includes two packages for running MoveIt Studio:

- `moveit_studio_za6_base_config`:  The base Studio configuration
- `moveit_studio_za6_tending_config`:  The machine tending
  configuration with a Tormach PCNC 1100 milling machine

Everything needed to run a Tormach ZA robot from the hardware drivers
to the MoveIt! configuration is included, along with scripts to build
the complete stack into a Docker image.  The Docker image can be used
on the Tormach robot controller to run real hardware, and can also be
used on any host with Docker engine to run in sim mode.

## Setup with Forked MoveIt2 (feature/forked-moveit2 branch)

**Important**: The `feature/forked-moveit2` branch requires building MoveIt2 from a forked source that includes ZA6-specific patches. This setup prevents the Docker image from installing upstream MoveIt2 packages, ensuring only the patched version is used.

### Workspace Setup

Create a ROS 2 workspace and clone the required repositories:

```bash
# Create workspace
mkdir -p ~/za6_workspace/src
cd ~/za6_workspace/src

# Clone the forked MoveIt2 repository with ZA6 patches
git clone <your-moveit2-fork-url> moveit2
cd moveit2
git checkout feature/za6-teleoperation
cd ..

# Clone additional MoveIt2 dependencies
# These are required by MoveIt2 but are separate repositories
git clone https://github.com/ros-planning/moveit_msgs.git -b humble
git clone https://github.com/ros-planning/moveit_resources.git -b humble

# Clone this repository
git clone <your-tormach-za-ros2-drivers-fork-url> tormach_za_ros2_drivers
cd tormach_za_ros2_drivers
git checkout feature/forked-moveit2
cd ../..
```

Your workspace structure should look like:
```
za6_workspace/
└── src/
    ├── moveit2/                  # Forked MoveIt2 with ZA6 servo patches
    ├── moveit_msgs/              # MoveIt messages (required dependency)
    ├── moveit_resources/         # MoveIt resources (required dependency)  
    └── tormach_za_ros2_drivers/  # This repository (feature/forked-moveit2)
```

### Building the Docker Image

Build the Docker image from the workspace root:

```bash
cd ~/za6_workspace
./src/tormach_za_ros2_drivers/devel_scripts/docker-dev.sh -b
```

### Building the Workspace

After the Docker image is built, launch the container and build the workspace:

```bash
# Launch container
./src/tormach_za_ros2_drivers/devel_scripts/docker-dev.sh

# Inside the container:
cd ~/za6_workspace
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

**Note:** The first build will take 10-20 minutes as MoveIt2 is compiled from source. If you encounter missing dependency errors during the build, ensure you're using the latest Docker image (see image version bumping below).

### About the MoveIt2 Patches

The forked MoveIt2 repository includes patches to MoveIt Servo that change hardcoded Franka Panda robot defaults to ZA6-specific values:

- `robot_link_command_frame`: `panda_link0` → `tool0`
- `command_out_topic`: `/panda_arm_controller/joint_trajectory` → `/joint_trajectory_controller/joint_trajectory`
- `move_group_name`: `panda_arm` → `manipulator`
- `planning_frame`: `panda_link0` → `world`
- `ee_frame_name`: `panda_link8` → `grasp_link`

See `patches/README.md` in this repository for details on the patch file.

The `feature/forked-moveit2` branch of this repository configures the Docker build to skip all upstream MoveIt2 apt packages, ensuring that only the patched version from source is used.

## Building without Forked MoveIt2 (main branch - Standard Setup)

If using the standard `main` or `humble` branch (without forked MoveIt2), follow the simpler setup:

```bash
mkdir -p ~/tormach_za_ros2_ws/src
cd ~/tormach_za_ros2_ws
git clone https://github.com/tormach/tormach_za_ros2_drivers.git \
    src/tormach_za_ros2_drivers
./src/tormach_za_ros2_drivers/devel_scripts/docker-dev.sh -b
```

**NOTE:** Because the containerized `docker build` environment has
limited access to the host environment, the build will fail if running
on a Tormach controller with the EtherCAT master running.  Before
building, stop the master:

    sudo systemctl stop ethercat

## Running the ZA6 on ROS 2

Run the ZA6, either real hardware or in sim mode, in a Docker
container using the instructions in this section.  Real hardware will
only run on a Tormach robot controller with `RT_PREEMPT` kernel and OS
tuning needed for real-time control.

**WARNING**:  Running ROS 2 on the Tormach controller will update the
EtherCAT master, causing the ROS 1 controller to stop working.  See
"Restore ROS 1 compatibility" below for more info and a fix.

### Launch the Tormach ZA6 ROS 2 development container

Start the container with the `docker-dev.sh` script.

    ./src/tormach_za_ros2_drivers/devel_scripts/docker-dev.sh

This starts a shell in the newly-launched Docker container.
Additional container shells may be started in new terminals.

    docker exec -itu $USER ros2-devel bash

### Build the workspace

From within the container, build the ROS workspace containing this
repository.

    source /opt/ros/$ROS_DISTRO/setup.bash
    colcon build

### Launch hardware, MoveIt and RViz

Once the workspace is built, start the robot hardware, MoveIt
configuration and RViz:

    source install/setup.bash
    ros2 launch za6_bringup bringup.launch

Extra launch arguments; see the `za6_bringup` package `README.md`:

    hal_debug_level:=5    Enable verbose hardware debugging
    sim_mode:=true        Run sim HAL hardware

### Enable drives

The robot cannot move until motor power is supplied and drives are
enabled.

After powering on the robot control cabinet, supply motor power by
releasing e-stop and pressing the reset button.  The reset button
blue lamp will glow, indicating motor power is available.

In software, after hardware launch, enable drives via the ROS
service.  The main shell console will log detailed message about
drive state changes, and the motor brakes will make audible clicks
as they release.

    source install/setup.bash  # If running a new terminal
    ros2 service call /enable_drives std_srvs/srv/Trigger

Disable drives with another ROS service.

    ros2 service call /disable_drives std_srvs/srv/Trigger

If drives fail to enable, look for clues in the main shell console
logs.

Read the `README.md` files in the various `za6_*` source packages for
more information about available robot controls.

## Restore ROS 1 compatibility

The ROS 1 containers depend on an older EtherCAT master running on
the host.  The ROS 2 container updates the master when the Docker
container starts.  To revert the EtherCAT master to the older
version for running ROS 1, run this script with the `fix-ethercat`
argument.

    ./devel_scripts/launch_za_dist_image.sh fix-ethercat

## Launch MoveIt Studio with ZA6 support

To run MoveIt Studio, see `moveit_studio_za6_base_config/README.md`.
