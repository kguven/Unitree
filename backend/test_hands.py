import sys
import os
import time

# Add Inspire Hand SDK to path
sys.path.append(os.path.join(os.path.dirname(__file__), "inspire_hand_ws/inspire_hand_sdk"))

try:
    from inspire_hand_sdk import inspire_dds, inspire_hand_defaut
    print("PASS: Successfully imported inspire_hand_sdk")
except ImportError as e:
    print(f"FAIL: Could not import inspire_hand_sdk: {e}")
    sys.exit(1)

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize

class HandController:
    def __init__(self):
        self.points = 6
        self.right_hand_publisher = None
        self.left_hand_publisher = None
        
        if inspire_dds is None:
            return

        print("[Hand] Initializing Hand Publishers...")
        try:
            # Right Hand
            self.right_hand_publisher = ChannelPublisher("rt/inspire_hand/ctrl/r", inspire_dds.inspire_hand_ctrl)
            self.right_hand_publisher.Init()
            
            # Left Hand
            self.left_hand_publisher = ChannelPublisher("rt/inspire_hand/ctrl/l", inspire_dds.inspire_hand_ctrl)
            self.left_hand_publisher.Init()
        except Exception as e:
            print(f"[Hand] Init failed: {e}")

    def move_hand(self, side, angles):
        """
        side: 'r' or 'l'
        angles: list of 6 ints (0-1000). 0=Open, 1000=Closed.
        Indices: 0:Pinky, 1:Ring, 2:Middle, 3:Index, 4:ThumbBend, 5:ThumbRot
        """
        if inspire_dds is None: return
        
        cmd = inspire_hand_defaut.get_inspire_hand_ctrl()
        cmd.mode = 1 # Angle Mode
        cmd.angle_set = angles
        
        if side == 'r' and self.right_hand_publisher:
            self.right_hand_publisher.Write(cmd)
        elif side == 'l' and self.left_hand_publisher:
            self.left_hand_publisher.Write(cmd)
            
    def open_hand(self, side='both'):
        open_angles = [0, 0, 0, 0, 0, 0]
        if side in ['r', 'both']:
            self.move_hand('r', open_angles)
        if side in ['l', 'both']:
            self.move_hand('l', open_angles)
            
    def close_hand(self, side='both'):
        close_angles = [1000, 1000, 1000, 1000, 1000, 1000]
        if side in ['r', 'both']:
            self.move_hand('r', close_angles)
        if side in ['l', 'both']:
            self.move_hand('l', close_angles)

    def gesture(self, side, name):
        # 0:Pinky, 1:Ring, 2:Middle, 3:Index, 4:ThumbBend, 5:ThumbRot
        angles = [1000]*6 # Default Closed
        
        if name == "open":
            angles = [0]*6
        elif name == "close" or name == "rock":
            angles = [1000]*6
        elif name == "paper":
            angles = [0]*6
        elif name == "scissors":
            # Index(3) and Middle(2) Open (0), others Closed (1000)
            angles = [1000, 1000, 0, 0, 1000, 1000] 
        elif name == "peace":
             # Same as scissors essentially
            angles = [1000, 1000, 0, 0, 1000, 1000]
        elif name == "pointer":
            # Index Open
             angles = [1000, 1000, 1000, 0, 1000, 1000]

        if side in ['r', 'both']:
            self.move_hand('r', angles)
        if side in ['l', 'both']:
            self.move_hand('l', angles)

def test_hands():
    print("--------------------------------------------------")
    print("Running Inspire Hand Test...")
    print("--------------------------------------------------")
    
    # Init DDS
    try:
        ChannelFactoryInitialize(0, "eth0")
    except:
        pass # Might be initialized
    
    hands = HandController()
    
    print("\n[1] Testing Open Hands (Right)...")
    hands.open_hand('r')
    time.sleep(2)
    
    print("\n[2] Testing Close Hands (Right)...")
    hands.close_hand('r')
    time.sleep(2)
    
    print("\n[3] Testing Peace Sign (Right)...")
    hands.gesture('r', 'peace')
    time.sleep(2)
    
    print("\n[4] Testing Open Hands (Left)...")
    hands.open_hand('l')
    time.sleep(2)
    
    print("--------------------------------------------------")
    print("Test Complete.")

if __name__ == "__main__":
    test_hands()
