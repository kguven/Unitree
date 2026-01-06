import time
import sys
import os
import signal
import numpy as np

# Add SDK path
sys.path.append(os.path.join(os.path.dirname(__file__), "../unitree_sdk2_python"))

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize, ChannelPublisher
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.utils.crc import CRC

# Joint Indices (Copied from robot_controller.py for consistency)
class G1JointIndex:
    # Left arm - Matches g1_arm7_sdk_dds_example.py
    LeftShoulderPitch = 15
    LeftShoulderRoll = 16
    LeftShoulderYaw = 17
    LeftElbow = 18
    LeftWristRoll = 19
    LeftWristPitch = 20
    LeftWristYaw = 21
    
    # Right arm
    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbow = 25
    RightWristRoll = 26
    RightWristPitch = 27
    RightWristYaw = 28

    # Waist
    WaistYaw = 12
    WaistRoll = 13
    WaistPitch = 14
    
    kNotUsedJoint = 29

def main():
    print("Initializing Joint Reader...")
    print("Use Ctrl+C to exit.")
    
    try:
        ChannelFactoryInitialize(0)
    except:
        pass

    # Create Publisher for Damping Mode
    arm_sdk_publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
    arm_sdk_publisher.Init()
    
    # Create Subscriber for State
    lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
    state_container = {"low_state": None}
    
    def low_state_handler(msg: LowState_):
        state_container["low_state"] = msg
        
    lowstate_subscriber.Init(low_state_handler, 10)
    
    # Wait for data
    print("Waiting for robot state...")
    while state_container["low_state"] is None:
        time.sleep(0.1)
        
    print("State received. Starting Damping Mode loop...")
    
    low_cmd = unitree_hg_msg_dds__LowCmd_()
    crc_util = CRC()
    
    # Indices for display
    # (Matches G1JointIndex but mapped to 0-reference for list usage if we had a flat list, 
    # but LowState uses fixed array indices defined by SDK/IDL. 
    # Wait, G1JointIndex values 13-29 are the actual indices in motor_state array?)
    # Let's verify standard G1 SDK mapping. 
    # Usually Legs are 0-11. Waist 12-14. Arms 15-28?
    # Actually, let's trust the values I copied from robot_controller logic if they are correct.
    # In robot_controller I saw:
    # arm_joints = [G1JointIndex.LeftShoulderPitch, ...]
    # And used them as indices into motor_cmd[joint].
    
    # Let's list the joints we care about
    left_arm_indices = [
        G1JointIndex.LeftShoulderPitch, G1JointIndex.LeftShoulderRoll, G1JointIndex.LeftShoulderYaw,
        G1JointIndex.LeftElbow, G1JointIndex.LeftWristRoll, G1JointIndex.LeftWristPitch, G1JointIndex.LeftWristYaw
    ]
    
    right_arm_indices = [
        G1JointIndex.RightShoulderPitch, G1JointIndex.RightShoulderRoll, G1JointIndex.RightShoulderYaw,
        G1JointIndex.RightElbow, G1JointIndex.RightWristRoll, G1JointIndex.RightWristPitch, G1JointIndex.RightWristYaw
    ]
    
    all_controlled_joints = left_arm_indices + right_arm_indices

    try:
        while True:
            # 1. Send Damping Command (Safety First!)
            low_cmd.motor_cmd[G1JointIndex.kNotUsedJoint].q = 1 # Enable arm_sdk control logic
            
            for joint_idx in all_controlled_joints:
                low_cmd.motor_cmd[joint_idx].mode = 1 
                low_cmd.motor_cmd[joint_idx].q = 0.0 
                low_cmd.motor_cmd[joint_idx].dq = 0.0
                low_cmd.motor_cmd[joint_idx].kp = 0.0 
                low_cmd.motor_cmd[joint_idx].kd = 2.5 
                low_cmd.motor_cmd[joint_idx].tau = 0.0

            low_cmd.crc = crc_util.Crc(low_cmd)
            arm_sdk_publisher.Write(low_cmd)
            
            # 2. Read and Print Angles
            state = state_container["low_state"]
            if state:
                # Format Output
                l_q = [state.motor_state[i].q for i in left_arm_indices]
                r_q = [state.motor_state[i].q for i in right_arm_indices]
                
                # Check for Head?
                # C++ example implied low_cmd.head()[0]. Maybe state has it too?
                head_info = "N/A"
                try:
                    # Check standard attributes
                    if hasattr(state, 'motor_state'):
                        # Check length
                        if len(state.motor_state) > 30:
                             # Maybe head is at 30, 31?
                             h_q = [state.motor_state[i].q for i in range(30, min(35, len(state.motor_state)))]
                             head_info = f"Extra Motors: {h_q}"
                except:
                    pass
                
                print("\033[H\033[J", end="") # Clear console
                
                print("=== G1 Joint Reader (Damping Mode) ===")
                print(f"Indices: L={left_arm_indices[0]}-{left_arm_indices[-1]}, R={right_arm_indices[0]}-{right_arm_indices[-1]}")
                print("-" * 50)
                print("Right Arm (used for Giver):")
                print(f"  Shoulder Pitch : {r_q[0]:.2f}")
                print(f"  Shoulder Roll  : {r_q[1]:.2f}")
                print(f"  Shoulder Yaw   : {r_q[2]:.2f}")
                print(f"  Elbow          : {r_q[3]:.2f}")
                print(f"  Wrist Roll     : {r_q[4]:.2f}")
                print(f"  Wrist Pitch    : {r_q[5]:.2f}")
                print(f"  Wrist Yaw      : {r_q[6]:.2f}")
                print("-" * 20)
                print(f"FULL RIGHT ARRAY: [{', '.join([f'{x:.2f}' for x in r_q])}]")
                print("-" * 50)
                print(f"HEAD/EXTRA: {head_info}")
                
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
