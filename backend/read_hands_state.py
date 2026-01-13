import time
import sys
import threading
from dataclasses import dataclass

# --- Unitree SDK & IDL Definitions ---
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import MotorState_

class HandStateReader:
    def __init__(self):
        self.topic = "rt/inspire/state"
        print(f"Subscribing to G1 Hand States on topic: {self.topic}")
        
        self.subscriber = ChannelSubscriber(self.topic, HandState_)
        self.subscriber.Init(self.handler, 10)
        
        self.last_print = 0
        
    def handler(self, msg: HandState_):
        # Print at ~2Hz
        now = time.time()
        if now - self.last_print > 0.5:
            self.last_print = now
            self.print_state(msg)

    def print_state(self, msg: HandState_):
        # Clear line/screen or just print separator
        print("-" * 50)
        print(f"[{time.time():.2f}] G1 Hand State")
        
        # msg.motor_state is a list of MotorState_
        # Expected length: 12 (0-5 Left, 6-11 Right)
        
        if not hasattr(msg, 'motor_state'):
            print("  Malformed message: no motor_state field.")
            return

        count = len(msg.motor_state)
        if count == 0:
            print("  No motor data received.")
            return

        # Assuming standard mapping: 0-5 Left, 6-11 Right
        # Names for fingers: Pinky, Ring, Mid, Index, ThumbB, ThumbR
        finger_names = ["Pinky", "Ring ", "Mid  ", "Index", "ThumbB", "ThumbR"]
        
        print(f"  Total Motors: {count}")
        
        # Left Hand (0-5)
        print("  LEFT HAND:")
        for i in range(min(6, count)):
            q = msg.motor_state[i].q
            t = msg.motor_state[i].tau_est
            name = finger_names[i] if i < 6 else f"M{i}"
            print(f"    {name}: q={q:.2f}, tau={t:.2f}")

        # Right Hand (6-11)
        if count > 6:
            print("  RIGHT HAND:")
            for i in range(6, min(12, count)):
                q = msg.motor_state[i].q
                t = msg.motor_state[i].tau_est
                idx = i - 6
                name = finger_names[idx] if idx < 6 else f"M{i}"
                print(f"    {name}: q={q:.2f}, tau={t:.2f}")
        
    
def main():
    print("--- Unitree G1 Inspire Hand State Reader ---")
    
    if len(sys.argv) < 2:
        print("Usage: python3 read_hands_state.py <network_interface>")
        ChannelFactoryInitialize(0)
    else:
        ChannelFactoryInitialize(0, sys.argv[1])

    reader = HandStateReader()
    
    print("Listening for data... (Press Ctrl+C to quit)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
