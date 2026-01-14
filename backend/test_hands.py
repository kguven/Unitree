import time
import sys
import numpy as np

# Adjust sys.path to include the cloned SDK
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../inspire_hand_ws/inspire_hand_sdk"))

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from inspire_sdkpy import inspire_hand_defaut, inspire_dds

# Constants
START_IDX = 29
MOTOR_COUNT = 6
TOPIC_BASE = "rt/inspire_hand/ctrl/"

class HandController:
    def __init__(self, hand='r'):
        self.hand = hand
        self.cmd_topic = f"rt/inspire_hand/ctrl/{hand}"
        self.state_topic = f"rt/inspire_hand/state/{hand}"
        
        print(f"Initializing G1 Hand Publisher on topic: {self.cmd_topic}")
        self.publisher = ChannelPublisher(self.cmd_topic, inspire_dds.inspire_hand_ctrl)
        self.publisher.Init()
        
        print(f"Subscribing to G1 Hand State on topic: {self.state_topic}")
        self.subscriber = ChannelSubscriber(self.state_topic, inspire_dds.inspire_hand_state)
        self.subscriber.Init(self.state_handler, 10)
        self.latest_state = None

        self.cmd = inspire_hand_defaut.get_inspire_hand_ctrl()
        self.cmd.angle_set = [0] * 6
        self.cmd.pos_set = [0] * 6
        self.cmd.force_set = [0] * 6
        self.cmd.speed_set = [1000] * 6 

    def state_handler(self, msg):
        self.latest_state = msg

    def print_status(self):
        if self.latest_state:
            # Assuming angles are in angle_actual or similar field. 
            # I need to know the field names. 
            # Based on common IDL patterns: angle_actual, force_actual?
            # Let's inspect generic fields first or assume logic.
            # inspire_hand_state usually has: angle_activ, force_activ, etc.
            # Or similar to control: angle_set -> angle_get? WIll check.
            try:
                # Fallback to printing dict if uncertain
                print(f"State: Angles={list(self.latest_state.angle_actual)}")
            except:
                print(f"State: {self.latest_state}")
        else:
            print("No state data received yet.")

    def set_angles(self, angles):
        """
        angles: list of 6 values (0-1000 typically mapped to 0-1)
        """
        self.cmd.mode = 1 # 0b0001 Angle mode
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
        print("Usage: python3 test_hands.py <network_interface>")
        ChannelFactoryInitialize(0)
    else:
        ChannelFactoryInitialize(0, sys.argv[1])

    hands = []
    # Initialize both hands
    print("Initializing Hand Controllers...")
    try:
        r_hand = HandController('r')
        hands.append(r_hand)
    except Exception as e:
        print(f"Failed to init Right Hand: {e}")

    try:
        l_hand = HandController('l')
        hands.append(l_hand)
    except Exception as e:
        print(f"Failed to init Left Hand: {e}")

    if not hands:
        print("No hands initialized. Exiting.")
        return

    print("\nCommands (Applied to BOTH hands):")
    print("  o - Open")
    print("  c - Close")
    print("  w - Wave")
    print("  s - Print Status")
    print("  q - Quit")
    
    try:
        while True:
            key = get_key()
            if key:
                if key == 'q':
                    break
                elif key == 'o':
                    for h in hands: h.set_open()
                elif key == 'c':
                    for h in hands: h.set_close()
                elif key == 'w':
                    for h in hands: h.wave()
                elif key == 's':
                    for h in hands: 
                        print(f"[{h.hand.upper()}] ", end="")
                        h.print_status()
            time.sleep(0.01)

            
    except KeyboardInterrupt:
        pass
    
    print("Exiting...")


            


if __name__ == "__main__":
    main()
