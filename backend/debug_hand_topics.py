import time
import sys
import threading
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_, LowState_

# List of potential topics to check
TOPICS = [
    "rt/inspire/state",
    "rt/inspire_hand/state/r",
    "rt/inspire_hand/state/l",
    "rt/inspire/cmd"
]

class TopicSniffer:
    def __init__(self, topic, msg_type):
        self.topic = topic
        self.msg_type = msg_type
        print(f"Subscribing to {topic}...")
        self.sub = ChannelSubscriber(topic, msg_type)
        self.sub.Init(self.handler, 10)
        self.received = False

    def handler(self, msg):
        if not self.received:
            print(f"\n[SUCCESS] Received data on topic: {self.topic}")
            print(f"  Type: {type(msg)}")
            if hasattr(msg, 'motor_state'):
                print(f"  Motor Count: {len(msg.motor_state)}")
            self.received = True

def main():
    print("--- Hand Topic Sniffer v2 ---")
    if len(sys.argv) < 2:
        print("Usage: python3 debug_hand_topics.py <network_interface>")
    
    ChannelFactoryInitialize(0)
    
    sniffers = []
    
    # Check HandState_ topics
    for t in TOPICS:
        sniffers.append(TopicSniffer(t, HandState_))
        
    # Check LowState as well
    sniffers.append(TopicSniffer("rt/lowstate", LowState_))
        
    print("Listening for 10 seconds...")
    time.sleep(10)
    print("Done.")

if __name__ == "__main__":
    main()
