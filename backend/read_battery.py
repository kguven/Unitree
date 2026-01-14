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
            # BmsState_ has 'soc' (uint8), 'current' (int32), 'bmsvoltage' (array[uint32, 3])
            # Assuming bmsvoltage[0] is the main pack voltage in mV? 
            voltage = self.latest_msg.bmsvoltage[0] if len(self.latest_msg.bmsvoltage) > 0 else 0
            current = self.latest_msg.current
            soc = self.latest_msg.soc
            print(f"Battery SoC: {soc}% | Voltage: {voltage}mV | Current: {current}mA")
        else:
            print("Waiting for battery data...")

    def get_status(self):
        if self.latest_msg:
             voltage = self.latest_msg.bmsvoltage[0] if len(self.latest_msg.bmsvoltage) > 0 else 0
             return {
                "soc": self.latest_msg.soc,
                "voltage": voltage, # mV
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
