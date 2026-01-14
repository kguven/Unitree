import time
import sys
import threading
from dataclasses import dataclass

# --- Unitree SDK & IDL Definitions ---
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

class HandStateReader:
    def __init__(self):
        self.topic = "rt/lowstate"
        print(f"Subscribing to Robot LowState on topic: {self.topic}")
        
        self.subscriber = ChannelSubscriber(self.topic, LowState_)
        self.subscriber.Init(self.handler, 10)
        
        self.last_print = 0
        
    def handler(self, msg: LowState_):
        # Print at ~2Hz
        now = time.time()
        if now - self.last_print > 0.5:
            self.last_print = now
            self.print_state(msg)

    def print_state(self, msg: LowState_):
        # Clear line/screen or just print separator
        print("-" * 50)
        print(f"[{time.time():.2f}] G1 LowState Analysis")
        
        if not hasattr(msg, 'motor_state'):
            print("  Malformed message: no motor_state field.")
            return

        count = len(msg.motor_state)
        print(f"  Total Motors: {count}")
        
        # Standard G1 Body is usually 29 motors.
        # 0-11 Legs, 12-14 Waist, 15-28 Arms.
        # 29+ are likely Hands or Head.
        
        BODY_MOTOR_COUNT = 29
        
        if count <= BODY_MOTOR_COUNT:
            print("  No extra motors found (Hands might be disconnected or on different topic).")
            return

        print(f"  Extra Motors (Indices {BODY_MOTOR_COUNT}-{count-1}):")
        
        for i in range(BODY_MOTOR_COUNT, count):
            q = msg.motor_state[i].q
            t = msg.motor_state[i].tau_est
            print(f"    Motor {i}: q={q:.2f}, tau={t:.2f}")
            
        print("\n  Tip: Manually move the hands to see which values change.")

        
    
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
