# syntax = docker/dockerfile:1.2
###################################
# BUILD ARGUMENTS USED FOR IMAGE SPECIFICATION
###################################
#
# These arguments must be declared in Dockerfile before any
# FROM calls defining a build stage (otherwise the argument
# will be scoped to the preceding build image/stage)

ARG OS_VENDOR
ARG DEBIAN_SUITE
ARG BASE_OS_DOCKER_IMAGE

###################################
# BASE PUBLISHED IMAGE
###################################
#
# This stage is the common root of all others

FROM ${OS_VENDOR}:${DEBIAN_SUITE} AS base

# HTTP proxy for wget, etc.
ARG HTTP_PROXY
ENV http_proxy ${HTTP_PROXY}

ARG OS_VENDOR
ENV OS_VENDOR ${OS_VENDOR}

ARG DEBIAN_SUITE
ENV DEBIAN_SUITE ${DEBIAN_SUITE}

ARG WS_DIR=/root/ros_colcon_ws
ARG REPO_DIR=$WS_DIR/src/tormach_za_ros2_drivers
ARG DOCKER_DIR=$REPO_DIR/devel_scripts/docker
ARG EXPORT_DIR=$WS_DIR/ros-export

WORKDIR $DOCKER_DIR/

# Configure & update apt
# - Silence some Apt warnings & enable pkg cache
ENV DEBIAN_FRONTEND noninteractive
RUN echo 'APT::Install-Recommends "0";\nAPT::Install-Suggests "0";' > \
        /etc/apt/apt.conf.d/01norecommend \
    && echo 'APT::Get::Assume-Yes "true";' > \
        /etc/apt/apt.conf.d/02assumeyes \
    && rm -f /etc/apt/apt.conf.d/docker-clean
# - Set HTTP proxy for Apt
RUN test -z "${HTTP_PROXY}" || \
    echo "Acquire::http::Proxy \"${HTTP_PROXY}\";" \
    | tee /etc/apt/apt.conf.d/42proxy
# - fix apt-get hash sum problems with proxy
RUN bash -c "( \
        echo Acquire::http::Pipeline-Depth 0\\;; \
        echo Acquire::http::No-Cache true\\;; \
        echo Acquire::BrokenProxy    true\\;; \
        ) | tee /etc/apt/apt.conf.d/99fixbadproxy"
# - Upgrade packages
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update \
    && apt-get upgrade -y
# - Silence more Apt warnings
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update \
    && apt-get install -y \
        libfile-fcntllock-perl \
        apt-utils

# Cookie variable for container build environment
ENV ENV_COOKIE docker-build

# Settings
COPY devel_scripts/docker/env.sh .

# ROS distro, e.g. melodic
ARG ROS_DISTRO
ENV ROS_DISTRO ${ROS_DISTRO}

COPY devel_scripts/docker/base/ base/

# Update system & install general dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    base/1-system.sh

ENV \
    # Set locale for tools such as "black" to work correctly
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    # Qt build configuration
    QT_SELECT=5 \
    QT_X11_NO_MITSHM=1

###################################
# ROS BASE PUBLISHED IMAGE
###################################
#
# This stage adds Qt5, upstream ROS deps and Machinekit to the
# published image

FROM base AS ros_base
COPY devel_scripts/docker/ros_base/ ros_base/

# update to force ROS package reinstall
ENV PACKAGE_UPDATE_SERIAL=2

# ROS
# - Install ROS base packages
RUN --mount=type=cache,target=/var/cache/apt \
    ros_base/1-install-ros.sh

ENV ROS_VERSION=2


###################################
# ROS CUSTOM BUILD IMAGE
###################################
#
# This temporary build stage builds external customized (e.g. rviz) or
# new (e.g. hal_ros_control) ROS packages not in upstream ROS

FROM ros_base AS ros_custom_build
# update whenever we need to update the external packages
ENV PACKAGE_UPDATE_SERIAL=24
COPY devel_scripts/docker/ros_custom/ ros_custom/

# Set up ROS workspace and download custom package sources
RUN --mount=type=cache,target=/var/cache/apt,id=ros_custom \
    ros_custom/1-setup.sh
# Install ROS workspace package deps
RUN --mount=type=cache,target=/var/cache/apt,id=ros_custom \
    ros_custom/2-install-deps.sh
#  Build ROS workspace and install packages
RUN --mount=type=cache,target=/ccache/ \
    ros_custom/3-build.sh

###################################
# ROS CUSTOM PUBLISHED IMAGE
###################################
#
# This stage adds customized ROS packages, built from source, to the
# published image
#
# The result has all dependencies needed to build the packages in this
# repo

FROM ros_base AS ros_custom

COPY --from=ros_custom_build $EXPORT_DIR/ /

# Copy scripts used in later stages
COPY devel_scripts/docker/ros_custom/ ros_custom/
# Install ROS package deps
RUN --mount=type=cache,target=/var/cache/apt,id=ros_custom \
    ros_custom/run_rosdep.sh
# Install MoveIt2 build dependencies (when building from source)
RUN --mount=type=cache,target=/var/cache/apt,id=ros_custom \
    ros_custom/install_moveit2_deps.sh

###################################
# ROS DEVEL/DIST COMMON BUILD IMAGE
###################################
#
# This stage computes a final build dependency list for the packages
# in this repo
#
# We don't want to bloat the image with the build workspace, so this
# stage is an out-of-band build stage

FROM ros_custom as ros_d_common_build

# Copy repo package sources and generate (but don't install)
# dependency list
COPY za6_bringup    $REPO_DIR/za6_bringup
COPY za6_description $REPO_DIR/za6_description
COPY za6_hardware $REPO_DIR/za6_hardware
COPY za6_moveit_config $REPO_DIR/za6_moveit_config
COPY za6_tools $REPO_DIR/za6_tools

RUN ros_custom/run_rosdep.sh no_install

###################################
# ROS DEVEL/DIST COMMON PUBLISHED IMAGE
###################################
#
# This stage performs final steps common to both devel and dist images:
# - Install build dependencies for the packages in this repo
# - Set up common environment
#
# Since it is the last common layer at the top of the stack, it can
# also be used as a an easy way to add things in both images without a
# massive rebuild (but this shouldn't be abused!).

FROM ros_custom as ros_d_common
COPY devel_scripts/docker/ros_d_common/ ros_d_common/

# Install build deps generated in ros_d_common_build stage
COPY --from=ros_d_common_build \
    $DOCKER_DIR/base/install_local_package_deps.sh \
    base/install_local_package_deps.sh
RUN --mount=type=cache,target=/var/cache/apt,id=ros_d_common \
    apt-get update \
    && bash -xe base/install_local_package_deps.sh
# Replace any source-built packages clobbered by .deb packages
COPY --from=ros_custom_build $EXPORT_DIR/opt /opt

# Install misc. resources
# - Entrypoint script
RUN ros_d_common/1-install-check-cleanup.sh
# - X server for Virtual PathPilot
#     FIXME This should go earlier...
RUN --mount=type=cache,target=/var/cache/apt,id=ros_d_common \
    ros_d_common/2-xvfb.sh
# - Editors
RUN --mount=type=cache,target=/var/cache/apt,id=ros_d_common \
    ros_d_common/3-editor.sh
#  - Other misc. configuration
RUN --mount=type=cache,target=/var/cache/apt,id=ros_d_common \
    ros_d_common/4-misc.sh

# Run-time environment
ENTRYPOINT ["/usr/bin/entrypoint"]
# - If no args to `docker run`, start an interactive shell
CMD ["/bin/bash", "--login", "-i"]

# - Robot model and robot package
ARG ROBOT_MODEL=za
ARG ROBOT_PACKAGE=za6_robot

ENV \
    # Disable Python .local import path
    PYTHONNOUSERSITE=True \
    # Cookie variable for container run environment
    ENV_COOKIE=docker-run \
    # Robot model and package
    ROBOT_MODEL=${ROBOT_MODEL} \
    ROBOT_PACKAGE=${ROBOT_PACKAGE} \
    # ROS log output formatting:  show node and logger names
    RCUTILS_CONSOLE_OUTPUT_FORMAT="[{severity} {time}] [{name}]: {message} ({function_name}() at {file_name}:{line_number})" \
    RCUTILS_LOGGING_BUFFERED_STREAM=1 \
    PPRUSER=virtualpathpilot \
    QT_API=pyqt5 \
    # Cyclone DDS seems to be the preferred DDS implementation
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    # - Cribbed from MoveIt Studio container; needs review
    CYCLONEDDS_NETWORK_INTERFACE=lo \
    CYCLONEDDS_USE_MULTICAST=false \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    CYCLONEDDS_PEER_ADDRESSES=127.0.0.1 \
    CYCLONEDDS_URI=/etc/cyclonedds.xml

# Set up Virtual PathPilot user
RUN ros_d_common/5-user-setup.sh

###################################
# ROS DISTRIBUTION BUILD IMAGE
###################################
#
# This temporary stage builds the packages from this repo
#
# It is out-of-band to avoid adding bloat to the Docker image

FROM ros_d_common AS ros_dist_build

COPY za6_bringup    $REPO_DIR/za6_bringup
COPY za6_description $REPO_DIR/za6_description
COPY za6_hardware $REPO_DIR/za6_hardware
COPY za6_moveit_config $REPO_DIR/za6_moveit_config
COPY za6_tools $REPO_DIR/za6_tools

# Install apt and pip deps required by ROS packages
RUN --mount=type=cache,target=/var/cache/apt,id=ros_dist \
    ros_custom/run_rosdep.sh
# Build & install
RUN --mount=type=cache,target=/ccache/ \
    ros_custom/run_colcon_build.sh
# Build & install again, this time into $DESTDIR
RUN --mount=type=cache,target=/ccache/ \
    DESTDIR=$EXPORT_DIR \
        ros_custom/run_colcon_build.sh

###################################
# BASE OS PACKAGES BUILD IMAGE
###################################
#
# This stage builds the Debian packages from this repo
#
# Since the Debian packages should be always build in minimal
# environment and using the correct set of programs from a Debian
# suite, stage must be an out-of-band build stage

FROM ${BASE_OS_DOCKER_IMAGE} as base_os_package_build
COPY devel_scripts/robot_starter /tmp/debbuild/robot_starter
COPY devel_scripts/docker/base_os_package_build/ base_os_package_build/

ENV TERM=dumb

# Apt config:  silence warnings and set defaults
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true
ENV LC_ALL=C.UTF-8
ENV LANGUAGE=C.UTF-8
ENV LANG=C.UTF-8

# Turn off recommends on container OS
RUN printf "%s;\n%s;\n"                 \
    'APT::Install-Recommends "0"'       \
    'APT::Install-Suggests "0"'         \
    > /etc/apt/apt.conf.d/01norecommend

# Prepare the Debian packaging environment
RUN --mount=type=cache,target=/var/cache/apt,id=package_build \
    base_os_package_build/0-debian-ubuntu-packaging-tools.sh
# Build the 'pathpilotrobotstarter' package
RUN --mount=type=cache,target=/var/cache/apt,id=package_build \
    base_os_package_build/1-build-robot-starter-package.sh


###################################
# ROS DISTRIBUTION IMAGE
###################################
#
# This stage copies the built Debian packages from this repo
# into the published image for distribution
#
# The result is the final distribution image

FROM ros_d_common AS ros_dist

# Copy packages built from this repo
COPY --from=ros_dist_build $EXPORT_DIR/opt /opt
COPY --from=ros_dist_build \
    $REPO_DIR/src/robot_command/examples/programs \
    /opt/pathpilot/robot_examples
COPY --from=base_os_package_build /opt/pathpilot/robot /opt/pathpilot/robot

# Install DIST image final stuff
COPY devel_scripts/docker/ros_dist/ ros_dist/
RUN ros_dist/0-robot-program-examples.sh

# Final cleanup
WORKDIR /
RUN rm -rf $WS_DIR

# Distribution release version
ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}
LABEL com.tormach.pathpilot.robot.version=${RELEASE_VERSION}

# Image type
ENV IMAGE_TYPE=dist
LABEL com.tormach.pathpilot.robot.image.type=dist
# This is needed because of backward compatibility - launch-pathpilot-launcher
# distributed to Beta users requires the IMAGE_TYPE label
LABEL IMAGE_TYPE=dist

# Set image version
ARG IMAGE_VERSION
ENV IMAGE_VERSION=${IMAGE_VERSION}
LABEL com.tormach.pathpilot.robot.image.version=${IMAGE_VERSION}

# Set git SHA from which image was build
ARG GIT_REV
ENV GIT_REV=${GIT_REV}
LABEL com.tormach.pathpilot.robot.git.rev=${GIT_REV}

# Set OCI registry
ENV DOCKER_REGISTRY=docker.pathpilot.com

# Set prompt
RUN echo "ros2-${IMAGE_TYPE}@${IMAGE_VERSION}" > /etc/debian_chroot

###################################
# ROS DEVEL BUILD IMAGE
###################################
#
# This temporary build stage builds extra development tools
#
# This temporary stage builds the tools
#
# Since the tools have become quite complex and are added only to the
# devel image at the last stage, this is now in a separate build stage
# based on earlier, less-often-changed layers to avoid major rebuilds
# after small changes.

FROM ros_base AS ros_devel_build
COPY devel_scripts/docker/ros_devel/ ros_devel/

# Build devel stuff
RUN --mount=type=cache,target=/var/cache/apt,id=ros_devel \
    ros_devel/0-build.sh


###################################
# ROS DEVEL IMAGE
###################################
#
# This build stage copies development tools from the devel build stage
#
# The result is the final development image

FROM ros_d_common AS ros_devel

# Devel-specific environment
ENV \
    # Speed builds with ccache
    PATH=/usr/lib/ccache:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
    # ROS across multiple Docker sessions
    ROS_IP=127.0.0.1 \
    ROS_MASTER_URI=http://127.0.0.1:11311

# Install devel stuff
COPY devel_scripts/docker/ros_devel/ ros_devel/
COPY --from=ros_devel_build /usr/local /usr/local
RUN --mount=type=cache,target=/var/cache/apt,id=ros_devel \
    ros_devel/1-tools.sh

# Distribution release version
ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}
LABEL com.tormach.pathpilot.robot.version=${RELEASE_VERSION}

# Image type
ENV IMAGE_TYPE=devel
LABEL com.tormach.pathpilot.robot.image.type=devel

# Set image version
ARG IMAGE_VERSION
ENV IMAGE_VERSION=${IMAGE_VERSION}
LABEL com.tormach.pathpilot.robot.image.version=${IMAGE_VERSION}

# Set git SHA from which image was build
ARG GIT_REV
ENV GIT_REV=${GIT_REV}
LABEL com.tormach.pathpilot.robot.git.rev=${GIT_REV}

# Set OCI registry
ENV DOCKER_REGISTRY=docker.io

# Set prompt
RUN echo "ros2-${IMAGE_TYPE}@${IMAGE_VERSION}" > /etc/debian_chroot
