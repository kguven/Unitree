import time
import sys
import math
import termios
import tty
import select
from dataclasses import dataclass

# --- Unitree SDK & IDL Definitions ---
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import MotorCmd_
from unitree_sdk2py.utils.crc import CRC

# Constants
# Assuming G1 Convention: Left (0-5), Right (6-11) or vice versa.
# Standard Unitree G1: Legs are L then R. Arms are L then R.
# So likely Hands are L then R.
HAND_LEFT_ID = 0
HAND_RIGHT_ID = 1

# Indices in the 12-motor array
# If we assume L then R:
ID_L_START = 0
ID_R_START = 6
MOTOR_COUNT_PER_HAND = 6
TOTAL_MOTORS = 12

# Limits (Radians approx)
# 0 = Open? 1.5 = Closed? 
# Inspire hands usually close with positive angle or specific range.
# We'll try 0.0 to 1.2 safe range.
LIMIT_OPEN = 0.0
LIMIT_CLOSED = 1.2

class HandController:
    def __init__(self):
        self.topic = "rt/inspire/cmd"
        
        print(f"Initializing G1 Hand Publisher on topic: {self.topic}")
        self.publisher = ChannelPublisher(self.topic, HandCmd_)
        self.publisher.Init()
        
        self.crc = CRC()

        # Initialize Message
        motor_cmds = [MotorCmd_(mode=1, q=0.0, dq=0.0, tau=0.0, kp=0.0, kd=0.0, reserve=[0]*3) for _ in range(TOTAL_MOTORS)]
        self.msg = HandCmd_(motor_cmd=motor_cmds, reserve=[0]*4)
        
        # Init default values
        for i in range(TOTAL_MOTORS):
            self.msg.motor_cmd[i].mode = 1 # Enable/Servo Mode
            self.msg.motor_cmd[i].q = 0.0 # Open
            self.msg.motor_cmd[i].dq = 0.0
            self.msg.motor_cmd[i].kp = 2.0 # Stiffness (Adjust as needed)
            self.msg.motor_cmd[i].kd = 0.1 # Damping
            self.msg.motor_cmd[i].tau = 0.0

        self._count = 0
        self._dir = 1
        
    def _get_indices(self, hand_side):
        """
        hand_side: 'L' or 'R' or 'B' (Both)
        """
        indices = []
        if hand_side in ['L', 'B']:
            indices.extend(range(ID_L_START, ID_L_START + MOTOR_COUNT_PER_HAND))
        if hand_side in ['R', 'B']:
            indices.extend(range(ID_R_START, ID_R_START + MOTOR_COUNT_PER_HAND))
        return indices
        
    def rotate_motors(self, hand_side):
        """
        Wave effect (Sine)
        """
        indices = self._get_indices(hand_side)
        
        # Calculate Sine Wave
        amplitude = (LIMIT_CLOSED - LIMIT_OPEN) / 2.0
        mid = (LIMIT_CLOSED + LIMIT_OPEN) / 2.0
        
        val = mid + amplitude * math.sin(self._count / 20.0 * math.pi)
        
        for i in indices:
            self.msg.motor_cmd[i].q = val
            self.msg.motor_cmd[i].kp = 2.0
            self.msg.motor_cmd[i].kd = 0.1
        
        self._publish()
        
        self._count += self._dir
        if self._count >= 40: self._dir = -1
        if self._count <= -40: self._dir = 1
        
        time.sleep(0.02) 

    def grip_hand(self, hand_side):
        indices = self._get_indices(hand_side)
        for i in indices:
            self.msg.motor_cmd[i].q = LIMIT_CLOSED
            self.msg.motor_cmd[i].kp = 3.0
            self.msg.motor_cmd[i].kd = 0.1
            
        self._publish()
        time.sleep(0.1)

    def stop_motors(self, hand_side):
        """Open/Release"""
        indices = self._get_indices(hand_side)
        for i in indices:
            self.msg.motor_cmd[i].q = LIMIT_OPEN
            self.msg.motor_cmd[i].kp = 1.0
            self.msg.motor_cmd[i].kd = 0.1
            
        self._publish()
        time.sleep(0.1)
        
    def _publish(self):
        # CRC check if required by SDK (MotorCmds usually requires it)
        # However, Python SDK `Write` might handle it or we assume user handles it.
        # Check if `crc` field exists
        if hasattr(self.msg, 'crc'):
            self.msg.crc = self.crc.Crc(self.msg)
            
        self.publisher.Write(self.msg)


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
    print("--- Unitree G1 Inspire Hand Control (MotorCmds) ---")
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_hands.py <network_interface>")
        ChannelFactoryInitialize(0)
    else:
        ChannelFactoryInitialize(0, sys.argv[1])

    hand_input = input("Select Hand (L/R/B): ").upper()
    if hand_input not in ['L', 'R', 'B']:
        hand_input = 'B'
        
    controller = HandController()
    
    print("\nCommands:")
    print("  r - Rotate (Wave)")
    print("  g - Grip (Close)")
    print("  s - Stop (Open)")
    print("  q - Quit")
    
    current_state = 'STOP'
    
    try:
        while True:
            key = get_key()
            if key:
                if key == 'q':
                    break
                elif key == 'r':
                    print("State: ROTATE")
                    current_state = 'ROTATE'
                elif key == 'g':
                    print("State: GRIP")
                    controller.grip_hand(hand_input)
                    current_state = 'GRIP'
                elif key == 's':
                    print("State: STOP")
                    controller.stop_motors(hand_input)
                    current_state = 'STOP'
            
            if current_state == 'ROTATE':
                controller.rotate_motors(hand_input)
            elif current_state == 'GRIP':
                controller.grip_hand(hand_input)
            elif current_state == 'STOP':
                controller.stop_motors(hand_input)
            
    except KeyboardInterrupt:
        pass
    
    print("Exiting...")
    controller.stop_motors(hand_input)

if __name__ == "__main__":
    main()
