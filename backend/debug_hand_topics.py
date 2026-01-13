import time
import sys
import threading
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_
try:
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import MotorStates_
except ImportError:
    MotorStates_ = None

# List of potential topics to check
TOPICS = [
    "rt/inspire/state",
    "rt/inspire_hand/state/r",
    "rt/inspire_hand/state/l",
    "rt/inspire/cmd" # Just to check if we can hear commands (loopback)
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
            self.received = True

def main():
    print("--- Hand Topic Sniffer ---")
    ChannelFactoryInitialize(0)
    
    sniffers = []
    
    # Check HandState_ topics
    for t in TOPICS:
        # We try HandState_ first
        sniffers.append(TopicSniffer(t, HandState_))
        
    print("Listening for 10 seconds...")
    time.sleep(10)
    print("Done.")

if __name__ == "__main__":
    main()
