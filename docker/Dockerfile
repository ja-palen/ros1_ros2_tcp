FROM ros:jazzy-ros-base
RUN apt-get update && apt-get install -y --no-install-recommends python3-yaml && rm -rf /var/lib/apt/lists/*
WORKDIR /gateway
COPY common /gateway/common
COPY ros2 /gateway/ros2
COPY config /gateway/config
CMD ["/bin/bash","-lc","source /opt/ros/jazzy/setup.bash && python3 /gateway/ros2/node.py /gateway/config/mappings.yaml"]
