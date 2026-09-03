# ROS1 <-> ROS2 TCP Topic Gateway

Generic Python gateway using a TCP socket to share topics from ROS1 to ROS2 and from ROS2 to ROS1.

- [ros1_node](./ros1/node.py): Gateway node for ROS2. Connects using a TCP socket to ROS1 node. 
- [ros2_node](./ros2/node.py): Gateway node for ROS1. Connects using a TCP socket to ROS2 node. 
- [maapings.yaml](./config/mappings.yaml): Mapping between ROS1 and ROS2 topics.
- [translador](./common/translator.py): Converts mapped ROS fields. 
- Wire format: `[4-byte big-endian payload length][UTF-8 JSON]`
- [tcp](./common/tcp.py): Handles framed JSON TCP transport.
- [docker](./docker/): Support for encapsulating ROS2 on a Docker container, as the main application of this tool is having ROS2 functionalities on a ROS1 host, where ROS1 and ROS2 distros are not compatible (host --> ROS Melodic and Docke r--> ROS Jazzy).

## Run

Run gateway node for ROS2 (Docker):
```bash
xhost +local:docker # For GUI applications
docker compose -f docker/compose.yaml build
docker compose -f docker/compose.yaml up
```

Run gateway node for ROS1:
```bash
source /opt/ros/noetic/setup.bash
export GATEWAY_DEBUG=1
python3 ros1/node.py config/mappings.yaml
```

The ROS2 container uses host networking and listens on 127.0.0.1:5000.
ROS1 connects to it.

## Test

### ROS2 -> ROS1:
Publish a mapped topic in ROS2, in this case, `/cmd_vel`.
```bash 
docker exec -it ros2_topic_gateway /bin/bash
source /opt/ros/jazzy/setup.bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist   "{linear: {x: 1.0}, angular: {z: 0.5}}"
```
Suscribe to the topic in ROS1.
```bash
rostopic echo /cmd_vel
```

### ROS1 -> ROS2
Publish a mapped topic in ROS1, in this case, `/odom`.
```bash
rostopic pub /odom nav_msgs/Odometry '{
  header: {frame_id: "odom"},
  child_frame_id: "base_link",
  pose: {
    pose: {
      position: {x: 1.0, y: 2.0, z: 0.0},
      orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
    }
  },
  twist: {
    twist: {
      linear: {x: 0.5, y: 0.0, z: 0.0},
      angular: {x: 0.0, y: 0.0, z: 0.1}
    }
  }
}' -r 10
```

Suscribe to the mapped topic in ROS2.
```bash
docker exec -it ros2_topic_gateway /bin/bash
source /opt/ros/jazzy/setup.bash
ros2 topic echo /odom
```

# TO-DO
- Better enconding (Protobuf) for heavy-loaded topics.
- Make tf_static robust to listener launched after talker.
