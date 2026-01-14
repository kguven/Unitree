import time
import sys
import numpy as np

# Adjust sys.path to include the cloned SDK
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../inspire_hand_ws/inspire_hand_sdk"))

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from inspire_sdkpy import inspire_hand_defaut, inspire_dds

# Constants
START_IDX = 29
MOTOR_COUNT = 6
TOPIC_BASE = "rt/inspire_hand/ctrl/"

class HandController:
    def __init__(self, hand='r'):
        self.hand = hand
        self.topic = f"rt/inspire_hand/ctrl/{hand}"
        
        print(f"Initializing G1 Hand Publisher on topic: {self.topic}")
        self.publisher = ChannelPublisher(self.topic, inspire_dds.inspire_hand_ctrl)
        self.publisher.Init()
        
        self.cmd = inspire_hand_defaut.get_inspire_hand_ctrl()
        # Ensure default initialization is safe
        self.cmd.angle_set = [0] * 6
        self.cmd.pos_set = [0] * 6
        self.cmd.force_set = [0] * 6
        self.cmd.speed_set = [1000] * 6 # Default speed? User example had 1000 in one place, 0 in another.
        
    def set_angles(self, angles):
        """
        angles: list of 6 values (0-1000 typically mapped to 0-1)
        """
        self.cmd.mode = 1 # 0b0001 Angle mode
        # User example used 1000 as a value. Assuming 0-1000 range for now or raw values.
        # "angle_set=[0,0,0,0,1000,1000]"
        # Let's handle generic inputs
        ensure_list = [int(a) for a in angles]
        if len(ensure_list) < 6:
            ensure_list.extend([0] * (6 - len(ensure_list)))
        self.cmd.angle_set = ensure_list[:6]
        self._publish()

    def set_open(self):
        print("Opening Hand (Angle 0)")
        self.set_angles([0] * 6)
        
    def set_close(self):
        print("Closing Hand (Angle 1000)")
        self.set_angles([1000] * 6)

    def wave(self):
        print("Waving...")
        for _ in range(3):
            self.set_close()
            time.sleep(0.5)
            self.set_open()
            time.sleep(0.5)

    def _publish(self):
        self.publisher.Write(self.cmd)
        
def get_key():
    import termios, tty, select
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
    print("--- Unitree G1 Inspire Hand Control ---")
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_hands.py <network_interface> [hand: r/l]")
        ChannelFactoryInitialize(0)
        hand_sel = 'r'
    else:
        ChannelFactoryInitialize(0, sys.argv[1])
        hand_sel = sys.argv[2] if len(sys.argv) > 2 else 'r'

    print(f"Selected Hand: {hand_sel.upper()}")
        
    controller = HandController(hand=hand_sel)
    
    print("\nCommands:")
    print("  o - Open")
    print("  c - Close")
    print("  w - Wave")
    print("  q - Quit")
    
    try:
        while True:
            key = get_key()
            if key:
                if key == 'q':
                    break
                elif key == 'o':
                    controller.set_open()
                elif key == 'c':
                    controller.set_close()
                elif key == 'w':
                    controller.wave()
            time.sleep(0.01)

            
    except KeyboardInterrupt:
        pass
    
    print("Exiting...")

if __name__ == "__main__":
    main()
