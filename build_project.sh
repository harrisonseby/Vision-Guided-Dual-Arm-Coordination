#!/bin/bash
set -e

# Source ROS 2 base and the prebuilt MoveIt2 overlay
source /opt/ros/humble/setup.bash
if [ -f /ros_ws_moveit2/install/setup.bash ]; then
  source /ros_ws_moveit2/install/setup.bash
fi

# Build the project workspace
cd /ros_ws_project
colcon build "$@"
