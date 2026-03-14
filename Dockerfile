# Use ROS Humble base image
FROM ros:humble

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    git \
    wget \
    curl \
    vim \
    nano \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install Navigation2 and related packages
RUN apt-get update && apt-get install -y \
    ros-$ROS_DISTRO-rviz2 \
    ros-$ROS_DISTRO-ros-gz \
    ros-$ROS_DISTRO-ros-gz-bridge \
    ros-$ROS_DISTRO-joint-state-publisher \
    ros-$ROS_DISTRO-joint-state-publisher-gui \
    ros-$ROS_DISTRO-rqt-joint-trajectory-controller \
    && rm -rf /var/lib/apt/lists/*
# Initialize rosdep
RUN rosdep update

# Create MoveIt2 workspace and build it once as part of the image
RUN mkdir -p /ros_ws_moveit2/src
WORKDIR /ros_ws_moveit2

# Copy MoveIt2 source into the image (only moveit2 packages are needed for the base build)
# Copy the contents of moveit2_parent_dir into src so colcon/rosdep finds packages directly under src
COPY src/moveit2_parent_dir/ ./src/

# Install MoveIt2 system dependencies and build it in Release mode (cached in image)
# Ensure universe repo is enabled so rosdep can find packages like libomp-dev
RUN add-apt-repository universe || true
RUN apt-get update
RUN /bin/bash -lc "source /opt/ros/humble/setup.bash && rosdep update"
RUN /bin/bash -lc "source /opt/ros/humble/setup.bash && rosdep install -r --from-paths src --ignore-src --rosdistro $ROS_DISTRO -y"
RUN /bin/bash -lc "source /opt/ros/humble/setup.bash && colcon build --event-handlers desktop_notification- status- --cmake-args -DCMAKE_BUILD_TYPE=Release"

# Create an empty workspace root for downstream builds (mounted at runtime)
# Your vision-guided dual-arm package will go under /ros_ws_project/src/vision_guided_dual_arm
RUN mkdir -p /ros_ws_project/src
WORKDIR /ros_ws_project

# Source ROS and MoveIt2 overlays in bashrc
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "if [ -f /ros_ws_moveit2/install/setup.bash ]; then source /ros_ws_moveit2/install/setup.bash; fi" >> ~/.bashrc
RUN echo "if [ -f /ros_ws_project/install/setup.bash ]; then source /ros_ws_project/install/setup.bash; fi" >> ~/.bashrc

# Copy helper scripts into the image
COPY ros_entrypoint.sh /ros_entrypoint.sh
COPY build_project.sh /usr/local/bin/build_project.sh
RUN chmod +x /ros_entrypoint.sh /usr/local/bin/build_project.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
