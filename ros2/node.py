#!/usr/bin/env python3
import os, sys, threading, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import rclpy
from rclpy.node import Node
from common.translator import load_config, load_type, Translator
from common.tcp import TCPServer

class Gateway(Node):
    def __init__(self, cfg):
        super().__init__("ros2_topic_gateway")
        self.cfg, self.debug = cfg, os.environ.get("GATEWAY_DEBUG") == "1"
        t = cfg.get("transport", {})
        self.tcp = TCPServer(t.get("host","127.0.0.1"), t.get("port",5000), self.debug)
        self.tcp.start()
        self.tr = {m["name"]: Translator(m,self.debug,side="ros2") for m in cfg["mappings"]}
        self.pub = {}
        for m in cfg["mappings"]:
            if m["direction"] == "ros2_to_ros1":
                typ = load_type(m["ros2"]["type"])
                self.create_subscription(typ, m["ros2"]["topic"], self.cb(m), 10)
            else:
                typ = load_type(m["ros2"]["type"])
                self.pub[m["name"]] = self.create_publisher(typ, m["ros2"]["topic"], 10)
        threading.Thread(target=self.accept_loop, daemon=True).start()
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def cb(self, m):
        def callback(msg):
            p = {"mapping":m["name"],"direction":"ros2_to_ros1",
                 "topic":m["ros1"]["topic"],"type":m["ros1"]["type"],
                 "fields":self.tr[m["name"]].encode(msg)}
            if not self.tcp.send(p):
                self.get_logger().warning("ROS1 peer not connected; dropped %s" % m["name"])
        return callback

    def accept_loop(self):
        while rclpy.ok(): self.tcp.accept()

    def receive_loop(self):
        while rclpy.ok():
            p = self.tcp.receive()
            if not p: time.sleep(.05); continue
            name = p.get("mapping")
            m = next((x for x in self.cfg["mappings"] if x["name"]==name), None)
            if not m or m["direction"] != "ros1_to_ros2": continue
            msg = load_type(m["ros2"]["type"])()
            self.tr[name].decode(p.get("fields",{}), msg)
            self.pub[name].publish(msg)

    def destroy_node(self):
        self.tcp.close()
        super().destroy_node()

def main():
    if len(sys.argv)!=2: print("Usage: node.py mappings.yaml"); return 1
    cfg=load_config(sys.argv[1]); rclpy.init(); n=Gateway(cfg)
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()
if __name__=="__main__": main()
