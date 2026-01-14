import time
import sys
import threading
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import BmsState_

class BatteryMonitor:
    def __init__(self, topic="rt/lf/bmsstate"):
        self.topic = topic
        print(f"Subscribing to {topic}...")
        self.sub = ChannelSubscriber(topic, BmsState_)
        self.sub.Init(self.handler, 10)
        self.latest_msg = None

    def handler(self, msg):
        self.latest_msg = msg

    def print_status(self):
        if self.latest_msg:
            # Adjust fields based on BmsState_ definition. 
            print(f"Battery SoC: {self.latest_msg.soc}% | Voltage: {self.latest_msg.voltage}mV | Current: {self.latest_msg.current}mA")
        else:
            print("Waiting for battery data...")

    def get_status(self):
        if self.latest_msg:
            return {
                "soc": self.latest_msg.soc,
                "voltage": self.latest_msg.voltage, # mV
                "current": self.latest_msg.current, # mA
                "valid": True
            }
        return {"soc": 0, "voltage": 0, "current": 0, "valid": False}

def main():
    print("--- Unitree G1 Battery Monitor ---")
    
    if len(sys.argv) < 2:
        print("Usage: python3 read_battery.py <network_interface>")
        ChannelFactoryInitialize(0)
    else:
        ChannelFactoryInitialize(0, sys.argv[1])
        
    monitor = BatteryMonitor()
    
    try:
        while True:
            monitor.print_status()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    print("Exiting...")

if __name__ == "__main__":
    main()
