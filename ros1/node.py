#!/usr/bin/env python3
import os, sys, time, threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import rospy
from common.translator import load_config, load_type, Translator
from common.tcp import TCPConnection

class Gateway:
    def __init__(self, cfg):
        rospy.init_node("ros1_topic_gateway")
        self.cfg, self.debug = cfg, os.environ.get("GATEWAY_DEBUG")=="1"
        t=cfg.get("transport",{})
        self.tcp=TCPConnection(t.get("host","127.0.0.1"),t.get("port",5000),
                               t.get("reconnect_seconds",1.0),self.debug)
        self.tr={m["name"]:Translator(m,self.debug,side="ros1") for m in cfg["mappings"]}
        self.pub={}
        for m in cfg["mappings"]:
            if m["direction"]=="ros1_to_ros2":
                typ=load_type(m["ros1"]["type"])
                rospy.Subscriber(m["ros1"]["topic"],typ,self.cb(m),queue_size=10)
            else:
                typ=load_type(m["ros1"]["type"])
                self.pub[m["name"]]=rospy.Publisher(m["ros1"]["topic"],typ,queue_size=10)
        threading.Thread(target=self.receive_loop,daemon=True).start()

    def cb(self,m):
        def callback(msg):
            if not self.tcp.connect(): return
            p={"mapping":m["name"],"direction":"ros1_to_ros2",
               "topic":m["ros2"]["topic"],"type":m["ros2"]["type"],
               "fields":self.tr[m["name"]].encode(msg)}
            self.tcp.send(p)
        return callback

    def receive_loop(self):
        while not rospy.is_shutdown():
            if not self.tcp.connect():
                time.sleep(.1); continue
            p=self.tcp.receive()
            if not p: time.sleep(.05); continue
            name=p.get("mapping")
            m=next((x for x in self.cfg["mappings"] if x["name"]==name),None)
            if not m or m["direction"]!="ros2_to_ros1": continue
            msg=load_type(m["ros1"]["type"])()
            self.tr[name].decode(p.get("fields",{}),msg)
            self.pub[name].publish(msg)

    def spin(self): rospy.spin()

def main():
    if len(sys.argv)!=2: print("Usage: node.py mappings.yaml"); return 1
    Gateway(load_config(sys.argv[1])).spin()
if __name__=="__main__": main()
