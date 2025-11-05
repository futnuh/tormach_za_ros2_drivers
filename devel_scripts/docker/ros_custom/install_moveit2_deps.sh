#!/bin/bash -xe
# Install MoveIt2 build dependencies
#
# These dependencies are needed when building MoveIt2 from source
# instead of using the pre-built apt packages.

WANT_ENV="docker-build docker-run"
. $(dirname $0)/../env.sh

apt-get update
apt-get install -y \
  ros-humble-object-recognition-msgs \
  ros-humble-octomap-msgs \
  ros-humble-octomap \
  ros-humble-eigen-stl-containers \
  ros-humble-random-numbers \
  ros-humble-geometric-shapes \
  ros-humble-srdfdom \
  ros-humble-ruckig \
  ros-humble-cv-bridge \
  ros-humble-image-transport \
  ros-humble-ompl \
  libfcl-dev \
  liboctomap-dev \
  libassimp-dev \
  libboost-all-dev \
  libbullet-dev \
  libeigen3-dev \
  libconsole-bridge-dev \
  freeglut3-dev \
  libgl1-mesa-dev \
  libglu1-mesa-dev

