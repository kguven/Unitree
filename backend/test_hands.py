import time
import sys
import math
import termios
import tty
import select
import threading
from dataclasses import dataclass
import numpy as np

# --- Unitree SDK & IDL Definitions ---
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
import cyclonedds.idl as idl
import cyclonedds.idl.annotations as annotate
import cyclonedds.idl.types as types

# Define inspire_hand_ctrl IDL structure inline
# Matches inspire_hand_ctrl.idl specific to Inspire Hand
@dataclass
@annotate.final
@annotate.autoid("sequential")
class inspire_hand_ctrl(idl.IdlStruct, typename="inspire.inspire_hand_ctrl"):
    pos_set: types.sequence[types.int16, 6]
    angle_set: types.sequence[types.int16, 6]
    force_set: types.sequence[types.int16, 6]
    speed_set: types.sequence[types.int16, 6]
    mode: types.int8

# Constants
MOTOR_MAX = 6
# Max/Min limits (approximate for Inspire Hand 0-1000 range)
# 0 = Open, 1000 = Closed
LIMIT_OPEN = 0
LIMIT_CLOSED = 1000

class HandController:
    def __init__(self, hand_id):
        """
        hand_id: 'L' or 'R'
        """
        self.hand_id = hand_id
        if hand_id == 'L':
            self.topic = "rt/inspire_hand/ctrl/l"
        else:
            self.topic = "rt/inspire_hand/ctrl/r"
            
        print(f"Initializing Publisher for {self.hand_id} Hand on topic: {self.topic}")
        self.publisher = ChannelPublisher(self.topic, inspire_hand_ctrl)
        self.publisher.Init()
        
        self.msg = inspire_hand_ctrl(
            pos_set=[0]*6,
            angle_set=[0]*6,
            force_set=[0]*6,
            speed_set=[0]*6,
            mode=0
        )
        
        self._count = 0
        self._dir = 1
        
    def rotate_motors(self):
        """
        Simulate 'Rotate' (Wave) effect using Sine wave on angles.
        Inspire Hand Range: 0-1000
        """
        # Mode 1: Angle Control
        # Binary: 0001
        self.msg.mode = 1 
        
        # Reset other fields
        self.msg.pos_set = [0]*6
        self.msg.force_set = [0]*6
        self.msg.speed_set = [0]*6 # Default speed? Or specific?
        
        # Calculate Sine Wave
        # Period ~ 200 steps (if called loop is fast)
        amplitude = (LIMIT_CLOSED - LIMIT_OPEN) / 2.0
        mid = (LIMIT_CLOSED + LIMIT_OPEN) / 2.0
        
        val = mid + amplitude * math.sin(self._count / 50.0 * math.pi)
        int_val = int(max(0, min(1000, val)))
        
        # Apply to all fingers
        self.msg.angle_set = [int_val] * 6
        
        self.publisher.Write(self.msg)
        
        self._count += self._dir
        if self._count >= 100: self._dir = -1
        if self._count <= -100: self._dir = 1
        
        time.sleep(0.02) # 50Hz approx

    def grip_hand(self):
        """
        Close hand static.
        """
        self.msg.mode = 1 # Angle
        self.msg.angle_set = [LIMIT_CLOSED] * 6
        self.publisher.Write(self.msg)
        time.sleep(0.1)

    def stop_motors(self):
        """
        Open/Release hand.
        """
        self.msg.mode = 1 # Angle
        self.msg.angle_set = [LIMIT_OPEN] * 6
        self.publisher.Write(self.msg)
        time.sleep(0.1)


# --- Input Handling ---

def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
        if rlist:
            key = sys.stdin.read(1)
            return key
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def main():
    print("--- Unitree/Inspire Hand Control (Python) ---")
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_hands.py <network_interface> (e.g. eth0)")
        # Defaulting to 0/eth0 for convenience inside IDE usually requires logic
        # But user follows C++ example which demands argv[1].
        # We will try to init default if not provided, for ease of use.
        print("Constructing default channel...")
        ChannelFactoryInitialize(0)
    else:
        ChannelFactoryInitialize(0, sys.argv[1])

    hand_input = input("Select Hand (L/R): ").upper()
    if hand_input not in ['L', 'R']:
        print("Invalid hand. Defaulting to R.")
        hand_input = 'R'
        
    controller = HandController(hand_input)
    
    print("\nCommands:")
    print("  r - Rotate (Wave)")
    print("  g - Grip (Close)")
    print("  s - Stop (Open)")
    print("  q - Quit")
    
    current_state = 'STOP'
    
    try:
        while True:
            # Check Input
            key = get_key()
            if key:
                if key == 'q':
                    break
                elif key == 'r':
                    print("State: ROTATE")
                    current_state = 'ROTATE'
                elif key == 'g':
                    print("State: GRIP")
                    controller.grip_hand() # Send once to ensure lock? or hold state?
                    current_state = 'GRIP'
                elif key == 's':
                    print("State: STOP")
                    controller.stop_motors()
                    current_state = 'STOP'
            
            # Loop Action
            if current_state == 'ROTATE':
                controller.rotate_motors()
            elif current_state == 'GRIP':
                # Re-send Grip to keep valid?
                controller.grip_hand()
            elif current_state == 'STOP':
                # Re-send Stop?
                controller.stop_motors()
                
            # Prevent busy loop if just holding (optional sleep handled in methods)
            
    except KeyboardInterrupt:
        pass
    
    print("Exiting...")
    controller.stop_motors()

if __name__ == "__main__":
    main()
