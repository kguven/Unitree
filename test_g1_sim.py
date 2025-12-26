import time
import sys
import numpy as np
import math

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.core.channel import ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread

G1_NUM_MOTOR = 29

# Values from control_parms.hpp (C++ Example)
# NOTE: C++ example had all 0.0 for q_init, implying the Zero Pose IS the standing pose for G1?
# Or maybe the C++ example 'stand_g1.cpp' sets them to specific values in my_controller.cpp?
# checking my_controller.cpp again... 
# It sets qref[i] = q_init[i]. 
# control_parms.hpp defines q_init as all zeros.
# So "Standing" might just be 0.0 for all joints on G1?
# Let's assume 0.0 is the "Zero Stiff Pose".

# Joint Indices
class G1JointIndex:
    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbow = 25
    RightWristRoll = 26
    RightWristPitch = 27
    RightWristYaw = 28

class Custom:
    def __init__(self):
        self.dt = 0.002 # 2ms
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state = None
        self.crc = CRC()
        self.running_time = 0.0
        
        self.lowcmd_publisher = None
        self.lowstate_subscriber = None
        self.lowCmdWriteThreadPtr = None

    def Init(self):
        self.lowcmd_publisher = ChannelPublisher("rt/lowcmd", LowCmd_)
        self.lowcmd_publisher.Init()

        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init(self.LowStateHandler, 10)
        self.InitLowCmd()

    def InitLowCmd(self):
        for i in range(G1_NUM_MOTOR):
            self.low_cmd.motor_cmd[i].mode = 0x01
            self.low_cmd.motor_cmd[i].q = 0.0
            self.low_cmd.motor_cmd[i].dq = 0.0
            self.low_cmd.motor_cmd[i].kp = 0.0
            self.low_cmd.motor_cmd[i].kd = 0.0
            self.low_cmd.motor_cmd[i].tau = 0.0
    
    def Start(self):
        self.lowCmdWriteThreadPtr = RecurrentThread(
            interval=self.dt, target=self.LowCmdWrite, name="control"
        )
        self.lowCmdWriteThreadPtr.Start()
        
    def LowStateHandler(self, msg: LowState_):
        self.low_state = msg

    def LowCmdWrite(self):
        self.running_time += self.dt
        
        # 1. BASE STABILITY
        # Reduce Kp to avoid vibration (was 80, try 60)
        # Hold all joints at Zero initially
        for i in range(G1_NUM_MOTOR):
            self.low_cmd.motor_cmd[i].q = 0.0
            self.low_cmd.motor_cmd[i].dq = 0.0
            self.low_cmd.motor_cmd[i].kp = 60.0 
            self.low_cmd.motor_cmd[i].kd = 3.5 # Slightly higher damping
            self.low_cmd.motor_cmd[i].tau = 0.0

        # 2. LEG LIFT ACTION (After 2.0s)
        if self.running_time > 2.0:
            lift_time = self.running_time - 2.0
            ratio = min(lift_time / 1.0, 1.0) # 1 second transition
            
            # Left Leg Joints (Indices 0-5 based on C++ comments)
            # 0: L_HipP, 1: L_HipR, 2: L_HipY, 3: L_Knee, 4: L_AnkleP, 5: L_AnkleR
            
            # Simple Lift: Flex Hip and Knee
            target_hip_pitch = -0.5  # Lift leg up (negative usually flexes hip forward/up)
            target_knee = 1.0        # Bend knee (positive usually bends backward)
            target_ankle = -0.5      # Compensate ankle
            
            # Apply to Left Leg
            self.low_cmd.motor_cmd[0].q = target_hip_pitch * ratio
            self.low_cmd.motor_cmd[3].q = target_knee * ratio
            self.low_cmd.motor_cmd[4].q = target_ankle * ratio
            
            # Decrease stiffness of lifted leg slightly to allow movement without fighting? 
            # Or keep high to hold pose? Keep high for now.

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.lowcmd_publisher.Write(self.low_cmd)

def main():
    print("------------------------------------------------")
    print("G1 Simulation: Stable Wave (Low Level)")
    print("------------------------------------------------")
    
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        print("Defaulting to 'lo' interface (Domain 0)...")
        ChannelFactoryInitialize(0, "lo")

    custom = Custom()
    custom.Init()
    custom.Start()

    while True:
        time.sleep(1.0)

if __name__ == '__main__':
    main()