# ROS1 <-> ROS2 TCP Topic Gateway

Generic Python gateway using a TCP socket and YAML field mappings.

ROS1 and ROS2 nodes own ROS communication. `common/translator.py` only converts
mapped ROS fields. `common/tcp.py` handles framed JSON TCP transport.

Wire format:
`[4-byte big-endian payload length][UTF-8 JSON]`

## Run

ROS2 (Docker):
```bash
docker compose -f docker/compose.yaml build
docker compose -f docker/compose.yaml up
```

ROS1:
```bash
source /opt/ros/noetic/setup.bash
export GATEWAY_DEBUG=1
python3 ros1/node.py config/mappings.yaml
```

The ROS2 container uses host networking and listens on 127.0.0.1:5000.
ROS1 connects to it.

Test ROS2 -> ROS1:
```bash
xhost +local:docker  
docker exec -it ros2_topic_gateway /bin/bash
source /opt/ros/jazzy/setup.bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist   "{linear: {x: 1.0}, angular: {z: 0.5}}"
```
Then on ROS1:
```bash
rostopic echo /cmd_vel
```

Add mappings in `config/mappings.yaml`; topic names/types are not hardcoded.
# ros1_ros2_tcp