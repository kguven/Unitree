import time
import sys
import threading
from dataclasses import dataclass

# --- Unitree SDK & IDL Definitions ---
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
import cyclonedds.idl as idl
import cyclonedds.idl.annotations as annotate
import cyclonedds.idl.types as types

# Define inspire_hand_state IDL structure inline
# Matches inspire_hand_state.idl specific to Inspire Hand
@dataclass
@annotate.final
@annotate.autoid("sequential")
class inspire_hand_state(idl.IdlStruct, typename="inspire.inspire_hand_state"):
    pos_act: types.sequence[types.int16, 6]
    angle_act: types.sequence[types.int16, 6]
    force_act: types.sequence[types.int16, 6]
    current: types.sequence[types.int16, 6]
    err: types.sequence[types.uint8, 6]
    status: types.sequence[types.uint8, 6]
    temperature: types.sequence[types.uint8, 6]

class HandStateReader:
    def __init__(self, hand_id):
        self.hand_id = hand_id
        if hand_id == 'L':
            self.topic = "rt/inspire_hand/state/l"
        else:
            self.topic = "rt/inspire_hand/state/r"
            
        print(f"Subscribing to {self.hand_id} Hand state on topic: {self.topic}")
        
        self.subscriber = ChannelSubscriber(self.topic, inspire_hand_state)
        self.subscriber.Init(self.handler, 10)
        
        self.last_print = 0
        
    def handler(self, msg: inspire_hand_state):
        # Print at ~2Hz to avoid console spam
        now = time.time()
        if now - self.last_print > 0.5:
            self.last_print = now
            self.print_state(msg)

    def print_state(self, msg: inspire_hand_state):
        # Clear line/screen or just print check
        # Indices: 0:Pinky, 1:Ring, 2:Middle, 3:Index, 4:ThumbBend, 5:ThumbRot
        print("-" * 50)
        print(f"[{self.hand_id} Hand State]")
        
        # Angles (0-1000)
        # Note: Depending on calibration, these are raw values 0-1000.
        angles = msg.angle_act
        names = ["Pinky", "Ring ", "Mid  ", "Index", "ThumbB", "ThumbR"]
        
        print("Joint Angles (0=Open, 1000=Closed):")
        for i, val in enumerate(angles):
            name = names[i] if i < len(names) else f"J{i}"
            print(f"  {name}: {val}")
            
        # Optional: Print Force or Status if needed
        # print(f"  Forces: {msg.force_act}")
        
    
def main():
    print("--- Unitree/Inspire Hand State Reader ---")
    
    if len(sys.argv) < 2:
        print("Usage: python3 read_hands_state.py <network_interface> (e.g. eth0)")
        ChannelFactoryInitialize(0)
    else:
        ChannelFactoryInitialize(0, sys.argv[1])

    hand_input = input("Select Hand to Monitor (L/R): ").upper()
    if hand_input not in ['L', 'R']:
        print("Invalid hand. Defaulting to R.")
        hand_input = 'R'
        
    reader = HandStateReader(hand_input)
    
    print("Listening for data... (Press Ctrl+C to quit)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
