#!/bin/bash -e
#
# Run `rosdep install` to install all apt and pip dependencies for ROS
# packages in /opt/ros/${ROS_DISTRO} and optionally ./src

WANT_ENV="docker-build docker-run"
. $(dirname $0)/../env.sh
set -x
BASE_SCRIPTS_DIR=${DOCKER_SCRIPTS_DIR}/base

ROSDEP_SKIP_KEYS=(
    # From OSRF ROS2 Docker image
    # https://github.com/osrf/docker_images/blob/master/ros2/nightly/nightly/Dockerfile#L116-L117
    # cyclonedds

    # RTI Connext requires accepting a license from RTI
    rmw_connextdds

    # Only needed for MoveIt Studio pkgs
    moveit_studio_agent
    moveit_studio_behavior

    # Skip MoveIt2 packages - we build from forked source with ZA6 patches
    # Note: moveit_msgs is a separate repo imported via vcs (see moveit2.repos)
    moveit_servo
    moveit_core
    moveit_ros_planning
    moveit_ros_move_group
    moveit_kinematics
    moveit_msgs
    moveit_planners
    moveit_planners_ompl
    moveit_planners_chomp
    pilz_industrial_motion_planner
    moveit_simple_controller_manager
    moveit_configs_utils
    moveit_ros_visualization
    moveit_ros_warehouse
    moveit_setup_assistant
    moveit_ros_occupancy_map_monitor
    moveit_ros_robot_interaction
    moveit_ros_planning_interface
    moveit_common
    moveit_setup_app_plugins
    moveit_setup_controllers
    moveit_setup_core_plugins
    moveit_setup_framework
    moveit_setup_srdf_plugins
    moveit_runtime
    moveit
    moveit_plugins
    moveit_ros
    chomp_motion_planner
    # Note: warehouse_ros and warehouse_ros_sqlite are external dependencies
    # and will be installed from apt packages
)

for DIR in ${WS_DIR}/src /opt/ros/${ROS_DISTRO}; do
    if test -d $DIR; then
        ROSDEP_ARGS+=" --from-paths $DIR"
    fi
done
ROSDEP_ARGS+=" ${ROSDEP_SKIP_KEYS[*]/#/--skip-keys=}"

cd ${WS_DIR}
if test -f /opt/ros/${ROS_DISTRO}/setup.bash; then
    # rosdep needs this to pick up package deps already installed
    # - don't exit at OpenRAVE env hook
    # https://github.com/jsk-ros-pkg/openrave_planning/blob/master/openrave/env-hooks/99.openrave.sh.in
    set +e
    source /opt/ros/${ROS_DISTRO}/setup.bash
    set -e
fi

# Create script to install ROS package dependencies
DEPS=${BASE_SCRIPTS_DIR}/install_local_package_deps.sh
# - Generate bash script
rosdep install --simulate --ignore-src ${ROSDEP_ARGS} >${DEPS}
cat ${DEPS}

# Run script
if test "$1" != no_install; then
    apt-get update
    bash -xe ${DEPS}
fi
