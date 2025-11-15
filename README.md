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

## Standard Setup (za6-devel / main branch)

Create a ROS 2 workspace and clone this repository:

```bash
mkdir -p ~/za6_workspace/src
cd ~/za6_workspace/src
git clone https://github.com/tormach/tormach_za_ros2_drivers.git
```

### Building the Docker Image

```bash
cd ~/za6_workspace
./src/tormach_za_ros2_drivers/devel_scripts/docker-dev.sh -b
```

### Launch the development container

```bash
./src/tormach_za_ros2_drivers/devel_scripts/docker-dev.sh
```

This drops you into a shell inside the new container. Start additional shells with:

```bash
docker exec -itu $USER ros2-devel bash
```

### Apply MoveIt Task Constructor patch

Our MTC integration relies on a small upstream patch (Python bindings,
execute callbacks, and controller smoothing). After cloning the
workspace—but before running the first build—apply the patch stored in
this repo:

```bash
cd ~/za6_workspace/src/moveit_task_constructor
git apply ../tormach_za_ros2_drivers/patches/0001-mtc-customizations.patch
```

Reapply the patch whenever you refresh the upstream
`moveit_task_constructor` source.

### Build the workspace

Inside the container:

```bash
cd ~/za6_workspace
source /opt/ros/$ROS_DISTRO/setup.bash
MAKEFLAGS=-j1 colcon build --symlink-install --executor sequential --parallel-workers 1 \
    --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_BUILD_PARALLEL_LEVEL=1
source install/setup.bash
```

The ZA6 controller has limited CPU headroom; forcing a single worker prevents colcon from
overwhelming the system. On a more capable workstation you can drop the throttling:

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install
source install/setup.bash
```

If you are building directly on a ZA6 controller, stop the legacy EtherCAT master before
running the Docker build or container:

```
sudo systemctl stop ethercat
```

## Legacy Setup with Forked MoveIt2 (feature/forked-moveit2 branch)

Older deployments used a forked MoveIt2 tree that bakes in ZA6-specific Servo patches.
If you need that workflow, check out the `feature/forked-moveit2` branch of this repo
and clone the MoveIt2, `moveit_msgs`, and `moveit_resources` repositories alongside it,
then follow the same Docker build steps above. See `patches/README.md` for details
on the Servo modifications in that branch.

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

### Apply MoveIt Task Constructor patch

Our MTC integration relies on a small upstream patch (Python bindings,
execute callbacks, and controller smoothing). After cloning the
workspace—but before running the first build—apply the patch stored in
this repo:

```bash
cd ~/za6_workspace/src/moveit_task_constructor
git apply ../tormach_za_ros2_drivers/patches/0001-mtc-customizations.patch
```

Reapply the patch whenever you refresh the upstream
`moveit_task_constructor` source.

### Build the workspace

From within the container, build the ROS workspace containing this
repository. On ZA6 controller hardware, keep the build single-threaded
to avoid CPU starvation:

    source /opt/ros/$ROS_DISTRO/setup.bash
    MAKEFLAGS=-j1 colcon build --symlink-install --executor sequential \
        --parallel-workers 1 --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1

> **Note**  
> The ZA6 controller has limited CPU headroom; forcing a single worker prevents colcon from
> overwhelming the system. Skip `--parallel-workers` if your host has more capacity.

### Launch hardware, MoveIt and RViz

Once the workspace is built, start the full teleop stack (HAL hardware, MoveIt, RViz, warehouse, Servo, gamepad bridge):

```
source install/setup.bash
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml \
  gamepad_config:=gamepad_config.yaml \
  db:=true
```

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
    export CYCLONEDDS_URI=/home/pathpilot/Projects/za6_workspace/install/za6_moveit_config/share/za6_moveit_config/config/cyclonedds.xml
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
