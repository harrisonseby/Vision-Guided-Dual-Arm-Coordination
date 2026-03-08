#!/bin/bash
set -e

# Source ROS setup
source /opt/ros/humble/setup.bash

# Source MoveIt2 overlay (built into the image)
if [ -f /ros_ws_moveit2/install/setup.bash ]; then
    source /ros_ws_moveit2/install/setup.bash
fi

# Source project overlay if it exists
if [ -f /ros_ws_project/install/setup.bash ]; then
    source /ros_ws_project/install/setup.bash
fi

# Execute the command
exec "$@"
