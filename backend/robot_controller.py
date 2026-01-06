import threading
import time
import random
import os
import requests
import datetime
import sys

# Add Inspire Hand SDK to path
sys.path.append(os.path.join(os.path.dirname(__file__), "inspire_hand_ws/inspire_hand_sdk"))
# Also need unitree_sdk2_python from the repo if it's there, but likely already installed globally or we use the local one.
# The repo structure: inspire_hand_ws/inspire_hand_sdk
# We need to be careful about imports.
# Let's try importing:
try:
    from inspire_hand_sdk import inspire_dds, inspire_hand_defaut
except ImportError:
    print("WARNING: Could not import inspire_hand_sdk. Hand control will be disabled.")
    inspire_dds = None
    inspire_hand_defaut = None
from . import ears
from . import mouth
from . import brain
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize, ChannelPublisher
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.utils.crc import CRC
import numpy as np
from dataclasses import dataclass
from dataclasses import dataclass

from . import custom
from . import wav_helper
from . import camera



kPi = 3.141592654
kPi_2 = 1.57079632

class G1JointIndex:
    # Left leg
    LeftHipPitch = 0
    LeftHipRoll = 1
    LeftHipYaw = 2
    LeftKnee = 3
    LeftAnklePitch = 4
    LeftAnkleB = 4
    LeftAnkleRoll = 5
    LeftAnkleA = 5

    # Right leg
    RightHipPitch = 6
    RightHipRoll = 7
    RightHipYaw = 8
    RightKnee = 9
    RightAnklePitch = 10
    RightAnkleB = 10
    RightAnkleRoll = 11
    RightAnkleA = 11

    # Waist (Torso)
    WaistYaw = 12
    WaistRoll = 13        # 29-DOF model has waist locked usually? But example lists them.
    WaistA = 13           
    WaistPitch = 14       
    WaistB = 14           

    # Left arm (7 DOF)
    LeftShoulderPitch = 15
    LeftShoulderRoll = 16
    LeftShoulderYaw = 17
    LeftElbow = 18
    LeftWristRoll = 19
    LeftWristPitch = 20   
    LeftWristYaw = 21     

    # Right arm (7 DOF)
    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbow = 25
    RightWristRoll = 26
    RightWristPitch = 27  
    RightWristYaw = 28    

    kNotUsedJoint = 29


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


class RobotController:

    def __init__(self):
        # Default to TRUE to match Phase 1 behavior (always on by default)
        self.chat_active = True 
        self.running = True
        self.lock = threading.Lock()
        
        # Initialize hardware
        self.asr_ready = ears.initialize_asr()
        if not self.asr_ready:
            print("WARNING: ASR not initialized")
        else:
             mouth.speak("System ready. Say Robot to activate me.")

        # Start background voice loop
        self.thread = threading.Thread(target=self._voice_loop, daemon=True)
        self.thread.start()
        
        # Audio Client
        self.audio_client = AudioClient()
        self.audio_client.SetTimeout(10.0)
        self.audio_client.Init()

        # Hand Controller
        self.hands = HandController()
        # Initial State: Open Hands?
        self.hands.open_hand()

        # Camera Controller
        self.camera = camera.RealSenseCamera()

        # Arm Control (Persistent Session)
        print("[Robot] Initializing Arm Control Interface...")
        try:
            ChannelFactoryInitialize(0)
        except:
            pass # Might be initialized globally or by another module
            
        self.arm_sdk_publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.arm_sdk_publisher.Init()
        
        self.state_container = {"low_state": None}
        self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_subscriber.Init(self._low_state_handler, 10)
        
        # Photo Upload State
        self.photo_active = False
        self.photo_interval = 60 # seconds
        self.photo_url = "http://localhost:5000/upload" # Default URL
        self.photo_thread = None

    def _low_state_handler(self, msg: LowState_):
        self.state_container["low_state"] = msg

    def _voice_loop(self):
        print("Voice loop started...")
        
        # Consistent State Logic from Phase 1
        # Loop: Wait for Wake Word -> Speak confirmation -> Listen for Command -> Think -> Speak
        
        while self.running:
            if not self.chat_active:
                time.sleep(0.5)
                continue

            # 1. Wait for Wake Word
            # ears.listen usually has a timeout. We use it to poll.
            try:
                # We are in "Wake Word Detection" mode
                text = ears.listen(timeout=1.0)
                if not text:
                    continue
                
                # Double check active state after blocking
                if not self.chat_active:
                    continue

                text_lower = text.lower()
                if "robot" in text_lower or "habibot" in text_lower:
                    print(f"[Wake] Detected in: '{text}'")
                    
                    # Lock for conversation turn
                    with self.lock:
                        mouth.speak("Habibot is listening.")
                    
                    # 2. Listen for Command
                    print("\n[State] Listening for command...")
                    user_input = ears.listen(timeout=8.0) # slightly longer for command
                    
                    if not user_input:
                        print("[State] No command received. Returning to wake word.")
                        continue
                        
                    # 3. Process Command (Stop logic + Gemini)
                    self.process_voice_command(user_input)

            except Exception as e:
                print(f"Error in voice loop: {e}")
                time.sleep(1)

    def process_voice_command(self, text):
        text_lower = text.lower()
        
        # Phase 1: Local Stop Logic
        stop_phrases = ["goodbye", "stop listening", "exit"]
        if any(phrase in text_lower for phrase in stop_phrases):
             print("[State] Stop command detected.")
             with self.lock:
                 mouth.speak("Okay, I'll be quiet.")
             return

        # Phase 1: Think (Gemini)
        print(f"[Thinking] {text}")
        response = brain.think(text)
        
        # Phase 1: Speak (Interruptible for Chat Mode)
        # We only allow interruption if we are just chatting, essentially answering questions.
        # This function 'process_voice_command' is the entry point.
        
        # Define interruption check
        def check_interruption():
            latest = ears.check_latest()
            if latest:
                print(f"[Interrupt] New command detected: {latest}")
                # We could filter 'robot' wake word here if it's required for interruption?
                # User said "voice commandde robot konusurken yen ibir komut..."
                # Usually we want any speech to interrupt? 
                # Yes, check_latest returns text if found.
            return latest

        with self.lock:
            interrupted_text = mouth.speak(response, interrupt_check=check_interruption)
            
        if interrupted_text:
            print(f"[Controller] Interrupted! Switching to new command: {interrupted_text}")
            # If interrupted, we need to handle the new command. 
            # Since we are outside the lock now (after the block), we can recurse.
            self.process_voice_command(interrupted_text)

    def set_chat_mode(self, active):
        print(f"Setting Chat Mode: {active}")
        self.chat_active = active
        with self.lock:
            if active:
                mouth.speak("I am listening.")
            else:
                mouth.speak("Audio off.")

    def trigger_action(self, action_id):
        """
        Execute one of the button scripts.
        """
        print(f"Triggering Action: {action_id}")
        
        # Run in a separate thread
        threading.Thread(target=self._run_action_script, args=(action_id,)).start()

    def _run_action_script(self, action_id):
        # Acquire lock to prevent Voice Loop from speaking over the action
        with self.lock:
            try:
                if action_id == "btn-1":
                    self.action_the_giver()
                elif action_id == "btn-2":
                    self.action_robot_sings()
                elif action_id == "btn-3":
                    self.action_standup_comedy()
                elif action_id == "btn-4":
                    self.action_living_statue()
                elif action_id == "btn-5":
                    self.action_fortune_teller()
                elif action_id == "btn-6":
                    self.action_selfie_mode()
                elif action_id == "btn-7":
                    self.action_rps_game()
                elif action_id == "btn-8":
                    self.action_the_butler()
                elif action_id == "btn-9":
                    self.action_wedding_toast()
                else:
                    print(f"Unknown action: {action_id}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Action failed: {e}")

    # --- PHOTO UPLOAD FEATURE ---

    def set_photo_mode(self, active):
        print(f"Setting Photo Mode: {active}")
        self.photo_active = active
        if active:
            if self.photo_thread is None or not self.photo_thread.is_alive():
                self.photo_thread = threading.Thread(target=self._photo_loop, daemon=True)
                self.photo_thread.start()
        # If inactive, the loop will exit on next iteration check

    def update_photo_settings(self, interval, url):
        print(f"Updating Photo Settings: Interval={interval}s, URL={url}")
        self.photo_interval = float(interval)
        self.photo_url = url

    def _photo_loop(self):
        print("Photo loop started...")
        
        # Start Camera
        self.camera.start()
        
        while self.photo_active and self.running:
            try:
                # Capture Photo
                print("[Photo] Capturing photo...")
                image_data = self.camera.capture_frame()
                
                if image_data:
                    # Upload
                    if self.photo_url:
                        print(f"[Photo] Uploading {len(image_data)} bytes to {self.photo_url}...")
                        try:
                            # Post as multipart/form-data
                            files = {'file': ('photo.jpg', image_data, 'image/jpeg')}
                            response = requests.post(self.photo_url, files=files, timeout=5)
                            print(f"[Photo] Upload Status: {response.status_code}")
                            
                            # Optional: Save locally for debug
                            # with open("last_photo.jpg", "wb") as f:
                            #     f.write(image_data)
                            
                        except Exception as e:
                            print(f"[Photo] Upload Failed: {e}")
                else:
                    print("[Photo] Failed to capture frame.")
                
                # Sleep for interval
                # Check status periodically to allow faster shutdown
                param_check_interval = 2.0
                waited = 0
                while waited < self.photo_interval:
                    if not self.photo_active or not self.running:
                        break
                    time.sleep(param_check_interval)
                    waited += param_check_interval
                    
            except Exception as e:
                print(f"Error in photo loop: {e}")
                time.sleep(5)
                
        # Stop Camera when loop ends
        self.camera.stop()
        print("Photo loop stopped.")


    # --- SAFE ARM CONTROL ---
    
    # --- SAFE ARM CONTROL ---
    
    def _move_arm_safe(self, target_config, duration=3.0, hold_time=0.0, return_to_start=True):
        """
        Executes a safe arm movement:
        1. Smoothly move from current Start to Target
        2. HOLD at Target
        3. (Optional) Smoothly move back to Start
        4. (Optional) Release Control
        """
        # Ensure we have state
        print("[SafeArm] Waiting for LowState...")
        wait_start = time.time()
        while self.state_container["low_state"] is None:
            time.sleep(0.1)
            if time.time() - wait_start > 5.0:
                print("[SafeArm] Timeout waiting for LowState!")
                return

        # Control Loop Parameters
        control_dt = 0.02
        current_time = 0.0
        kp = 60.0
        kd = 1.5
        
        # Arm Joints (Upper Limb - 7 DOF per arm + Waist)
        arm_joints = [
          G1JointIndex.LeftShoulderPitch,  G1JointIndex.LeftShoulderRoll,
          G1JointIndex.LeftShoulderYaw,    G1JointIndex.LeftElbow,
          G1JointIndex.LeftWristRoll,      G1JointIndex.LeftWristPitch,
          G1JointIndex.LeftWristYaw,
          G1JointIndex.RightShoulderPitch, G1JointIndex.RightShoulderRoll,
          G1JointIndex.RightShoulderYaw,   G1JointIndex.RightElbow,
          G1JointIndex.RightWristRoll,     G1JointIndex.RightWristPitch,
          G1JointIndex.RightWristYaw,
          G1JointIndex.WaistYaw,
          G1JointIndex.WaistRoll,
          G1JointIndex.WaistPitch
        ]

        low_cmd = unitree_hg_msg_dds__LowCmd_() 
        crc_util = CRC()
        
        # Capture Start Configuration
        start_config = []
        for joint in arm_joints:
             start_config.append(self.state_container["low_state"].motor_state[joint].q)

        # Handle 'None' in target_config (Station Keeping)
        final_target = []
        # Ensure target_config length matches
        if len(target_config) < len(arm_joints):
             target_config = list(target_config) + [None]*(len(arm_joints)-len(target_config))
             
        for i, val in enumerate(target_config):
            if val is None:
                final_target.append(start_config[i])
            else:
                final_target.append(val)
        
        print(f"[SafeArm] Starting movement loop (Duration={duration}s, Hold={hold_time}s, Return={return_to_start})...")
        
        # Phases Refined:
        # 0 to T: Move Directly from Start to Target
        # T to T+H: Hold
        # T+H to 2T+H: Move Back to Start (Only if return_to_start)
        # 2T+H to 3T+H: Release (Only if return_to_start)

        if return_to_start:
            total_time = (duration * 2.5) + hold_time 
        else:
            total_time = duration + hold_time
        
        while current_time < total_time:
            start_loop = time.time()
            current_time += control_dt
            
            low_cmd.motor_cmd[G1JointIndex.kNotUsedJoint].q = 1 # Enable arm_sdk
            
            if current_time < duration:
                 # [Stage 1]: Move Start -> Target
                 for i, joint in enumerate(arm_joints):
                    ratio = np.clip(current_time / duration, 0.0, 1.0)
                    low_cmd.motor_cmd[joint].tau = 0.
                    # Direct Interpolation
                    low_cmd.motor_cmd[joint].q = (1.0 - ratio) * start_config[i] + ratio * final_target[i]
                    low_cmd.motor_cmd[joint].dq = 0.
                    low_cmd.motor_cmd[joint].kp = kp
                    low_cmd.motor_cmd[joint].kd = kd
            
            elif current_time < (duration + hold_time):
                # [Stage 2]: HOLD
                for i, joint in enumerate(arm_joints):
                    low_cmd.motor_cmd[joint].tau = 0.
                    low_cmd.motor_cmd[joint].q = final_target[i]
                    low_cmd.motor_cmd[joint].dq = 0
                    low_cmd.motor_cmd[joint].kp = kp
                    low_cmd.motor_cmd[joint].kd = kd
                    
            elif return_to_start:
                if current_time < (duration * 2.0 + hold_time):
                    # [Stage 3]: Back to Start
                    for i, joint in enumerate(arm_joints):
                        ratio = np.clip((current_time - (duration + hold_time)) / duration, 0.0, 1.0)
                        low_cmd.motor_cmd[joint].tau = 0.
                        # Fade from Target back to Start
                        low_cmd.motor_cmd[joint].q = (1.0 - ratio) * final_target[i] + ratio * start_config[i]
                        low_cmd.motor_cmd[joint].dq = 0.
                        low_cmd.motor_cmd[joint].kp = kp
                        low_cmd.motor_cmd[joint].kd = kd

                else:
                     # [Stage 4]: Release
                     release_duration = duration * 0.5
                     ratio = np.clip((current_time - (duration * 2.0 + hold_time)) / release_duration, 0.0, 1.0)
                     low_cmd.motor_cmd[G1JointIndex.kNotUsedJoint].q = (1 - ratio) # Disable bit fading
                    

            
            # Write Command
            low_cmd.crc = crc_util.Crc(low_cmd)
            self.arm_sdk_publisher.Write(low_cmd)
            
            # Sleep remainder
            elapsed = time.time() - start_loop
            if elapsed < control_dt:
                time.sleep(control_dt - elapsed)
                
        print("[SafeArm] Movement complete.")

    # --- ACTION SCRIPTS ---
    # (Same as before, abbreviated for brevity where possible, but keeping full mocked logic)

    def action_the_giver(self):
        print("[MOTION] Extending Right Arm with card...")
        mouth.speak("Here is my card... take it!")
        
        # Target: Extend Right Arm
        # Indices: 7 (L), 7 (R), 3 (W) = 17 total
        # We use 'None' for left arm to keep it still
        
        # Open Hand
        self.hands.open_hand('r')

        target = [None] * 17
        
        target[7] = -0.44   # R_ShoulderPitch
        target[8] = 0.02   # R_ShoulderRoll
        target[9] = -0.03   # R_ShoulderYaw
        target[10] = 0.57 # R_Elbow
        target[11] = -0.04  # R_WristRoll
        target[12] = -0.13  # R_WristPitch
        target[13] = -0.05 # R_WristYaw
        self._move_arm_safe(target, duration=1.0, hold_time=0.5, return_to_start=False)
        target[7] = 0.69   # R_ShoulderPitch
        target[8] = -0.03   # R_ShoulderRoll
        target[9] = 0.10   # R_ShoulderYaw
        target[10] = -0.09 # R_Elbow
        target[11] = -0.04  # R_WristRoll
        target[12] = -0.37  # R_WristPitch
        target[13] = 0.14 # R_WristYaw
        self._move_arm_safe(target, duration=1.0, hold_time=1.0, return_to_start=False)

        print("[MOTION] Pulling arm back quickly!")
        mouth.speak("Ah! Too slow! Just kidding, here you go.")
        target[7] = -0.44   # R_ShoulderPitch
        target[8] = 0.02   # R_ShoulderRoll
        target[9] = -0.03   # R_ShoulderYaw
        target[10] = 0.57 # R_Elbow
        target[11] = -0.04  # R_WristRoll
        target[12] = -0.13  # R_WristPitch
        target[13] = -0.05 # R_WristYaw
        self._move_arm_safe(target, duration=1.0, hold_time=3.0, return_to_start=True)
        
        # Close hand
        self.hands.close_hand('r') 
        # _move_arm_safe goes back to zero automatically at the end of its cycle.
        # So we might just want to hold it? 
        # The current implementation does the full cycle: Zero -> Target -> Zero.
        # So "Pulling arm back" happens automatically in Stage 3!
        # Perfect for "The Giver" joke (extends then retracts).
        
    def action_robot_sings(self):
        mouth.speak("This next song is dedicated to the beautiful couple! Yalla!")
        
        # Audio playback in background thread so arm moves simultaneously
        def play_music():
            print("[AUDIO] Playing MP3: Nancy Ajram (test.wav)...")
            # Assuming running from 'backend' or root, adjust path
            # If running from app.py (root/web_app), .. is bad.
            # Best to use absolute path or relative to workspace
            audio_path = os.path.join(os.path.dirname(__file__), "../audio/test.wav")
            self.play_audio_file(audio_path)
            
        threading.Thread(target=play_music).start()
        
        # Dance move: Wave arms
        # Dance move: Wave arms (User Provided "Hand Wave")
        # Pos 1: [-0.37, -1.78, -1.34, 0.55, 0.02, 0.02, 0.06]
        # Pos 2: [-0.33, -1.47, -1.40, -0.64, -0.02, 0.17, 0.05]
        
        pos1 = [None] * 17
        pos1[7:14] = [-0.37, -1.78, -1.34, 0.55, 0.02, 0.02, 0.06]
        
        pos2 = [None] * 17
        pos2[7:14] = [-0.33, -1.47, -1.40, -0.64, -0.02, 0.17, 0.05]
        
        self.hands.open_hand('both')
        print("[MOTION] Waving Hand...")
        
        # Wave loop (3 times)
        for _ in range(3):
            self._move_arm_safe(pos1, duration=0.8, hold_time=0.1, return_to_start=False)
            self._move_arm_safe(pos2, duration=0.8, hold_time=0.1, return_to_start=False)
            
        # Return to start at end
        self._move_arm_safe(pos1, duration=1.0, hold_time=0.5, return_to_start=True)
        print("[MOTION] Wave complete")

    def play_audio_file(self, filename):
        if not os.path.exists(filename):
            print(f"[AUDIO] File not found: {filename}")
            return
            
        print(f"[AUDIO] Loading {filename}...")
        pcm_list, sample_rate, num_channels, is_ok = wav_helper.read_wav(filename)
        
        if not is_ok:
            print("[AUDIO] Failed to read WAV")
            return
            
        print(f"[AUDIO] Playing stream ({len(pcm_list)} bytes)...")
        wav_helper.play_pcm_stream(self.audio_client, pcm_list, stream_name="singing", sleep_time=0.5)
        self.audio_client.PlayStop("singing")
        print("[AUDIO] Playback finished.")

    def action_standup_comedy(self):
        prompt = "You are a Lebanese comedian. Tell a short, funny, sarcastic joke about traffic in Beirut or marriage."
        joke = brain.think(prompt)
        mouth.speak(joke)
        print("[MOTION] Shrug Shoulders (Comedia Pose)")
        
        # User Provided "Comedia" Pose (Right Arm)
        # [-0.18, -0.47, -0.51, 0.40, 0.33, 0.26, 0.06]
        shrug_target = [None] * 17
        
        # Right Arm (Index 7-13)
        shrug_target[7] = -0.18  # R_Pitch
        shrug_target[8] = -0.47  # R_Roll
        shrug_target[9] = -0.51  # R_Yaw
        shrug_target[10] = 0.40  # R_Elbow
        shrug_target[11] = 0.33  # R_WristRoll
        shrug_target[12] = 0.26  # R_WristPitch
        shrug_target[13] = 0.06  # R_WristYaw
        
        self.hands.open_hand('both')
        self._move_arm_safe(shrug_target, duration=1.0, hold_time=3.0)

        print("[AUDIO] Ba Dum Tss")
        # Restore/Run Custom Routine (Optional/Legacy check)
        # Removed legacy fallback block for cleaner code

    def action_living_statue(self):
        print("[MOTION] FREEZE MODE (Statue Pose)")
        # User Provided "Living Statue" Pose
        # [-0.21, -1.24, -1.10, 0.30, 0.21, -0.08, -0.01]
        
        statue_target = [None] * 17
        statue_target[7] = -0.21
        statue_target[8] = -1.24
        statue_target[9] = -1.10
        statue_target[10] = 0.30
        statue_target[11] = 0.21
        statue_target[12] = -0.08
        statue_target[13] = -0.01
        
        # Move to pose and freeze
        self._move_arm_safe(statue_target, duration=1.5, hold_time=5.0)
        
        print("[MOTION] Sudden Turn Left!")
        mouth.speak("Do you have a charging cable?!")

    def action_fortune_teller(self):
        mouth.speak("What is your sign? Tell me.")
        # We need to listen for the sign. 
        # Since we have the lock, the main loop is blocked. perfect.
        sign = ears.listen(timeout=5)
        if not sign:
            sign = "Leo"
        
        prompt = f"User said {sign}. Give a funny, 2-sentence horoscope prediction for this sign. Mention something about hummus or electricity."
        prediction = brain.think(prompt)
        mouth.speak(prediction)

    def action_selfie_mode(self):
        mouth.speak("Yalla, picture time! Everyone squeeze in!")
        print("[MOTION] Raise Left Arm (Peace Sign)")
        
        # User Provided "Selfie Mode" Poses (Right Arm recorded, assuming mirror for Left? 
        # Or did user mean Right? "Right Arm (used for Giver)" label is constant.
        # User output says "Right Arm". So we move RIGHT arm for Selfie?
        # Standard selfie is holding camera with one hand (Right?).
        # "1st position": [0.02, -0.26, 1.01, 1.28, 0.22, 0.00, -0.15]
        
        target = [None] * 17
        target[7] = 0.02
        target[8] = -0.26
        target[9] = 1.01
        target[10] = 1.28
        target[11] = 0.22
        target[12] = 0.00
        target[13] = -0.15
        
        # Peace Sign with OTHER hand? Or same?
        # If Right is holding camera, Left does peace.
        # User didn't give Left. We'll just open Right hand (Holding phone).
        self.hands.gesture('r', 'open') 
        
        print("[MOTION] Tilt Head") 
        # Execute Move and Hold
        # Pos 1
        self._move_arm_safe(target, duration=1.5, hold_time=2.0, return_to_start=False)
        # Pos 2 (Identical in user data, maybe slight adjust?)
        self._move_arm_safe(target, duration=1.0, hold_time=2.0, return_to_start=True)
        
        mouth.speak("Send me that on Instagram! I look great.")

    def action_rps_game(self):
        # User Provided RPS Poses
        # UP: [-0.07, -0.06, 0.28, 0.20, 0.04, -0.02, -0.25]
        # DOWN: [0.06, -0.08, 0.32, 0.64, 0.04, -0.08, 0.01]
        # SHOOT: [-0.86, -0.06, -0.16, 0.68, -0.02, 0.31, 0.22]
        
        up_target = [None] * 17
        up_target[7:14] = [-0.07, -0.06, 0.28, 0.20, 0.04, -0.02, -0.25]
        
        down_target = [None] * 17
        down_target[7:14] = [0.06, -0.08, 0.32, 0.64, 0.04, -0.08, 0.01]
        
        shoot_target = [None] * 17
        shoot_target[7:14] = [-0.86, -0.06, -0.16, 0.68, -0.02, 0.31, 0.22]

        # Swing 1
        mouth.speak("Rock...")
        print("[MOTION] Swing 1")
        self.hands.close_hand('r') 
        self._move_arm_safe(up_target, duration=0.4, hold_time=0.1, return_to_start=False)
        self._move_arm_safe(down_target, duration=0.4, hold_time=0.1, return_to_start=False)
        
        # Swing 2
        mouth.speak("Paper...")
        print("[MOTION] Swing 2")
        self._move_arm_safe(up_target, duration=0.4, hold_time=0.1, return_to_start=False)
        self._move_arm_safe(down_target, duration=0.4, hold_time=0.1, return_to_start=False)
        
        # Swing 3
        mouth.speak("Scissors...")
        print("[MOTION] Swing 3")
        self._move_arm_safe(up_target, duration=0.4, hold_time=0.1, return_to_start=False)
        
        # SHOOT
        mouth.speak("SHOOT!")
        choice = random.choice(["rock", "paper", "scissors"])
        print(f"[MOTION] Hand Pose: {choice}")
        
        def set_hand():
             self.hands.gesture('r', choice)
        threading.Thread(target=set_hand).start()
        
        self._move_arm_safe(shoot_target, duration=0.3, hold_time=2.0, return_to_start=True)
        
        mouth.speak(f"I chose {choice}!")
        time.sleep(1.0)
        self.hands.open_hand('r')

    def action_the_butler(self):
        print("[MOTION] Butler Pose (Tray)...")
        mouth.speak("Please, take one. I cannot eat, I am on a diet of pure lithium.")
        
        # User Provided "Butler" Pose
        # [-0.30, 0.06, 0.25, 0.60, 1.31, -0.10, 0.36]
        
        target = [None] * 17
        target[7] = -0.30  # Pitch
        target[8] = 0.06   # Roll
        target[9] = 0.25   # Yaw
        target[10] = 0.60  # Elbow
        target[11] = 1.31  # WristRoll
        target[12] = -0.10 # WristPitch
        target[13] = 0.36  # WristYaw
        
        # Open Hand
        self.hands.open_hand('r')
        
        # Move and Hold for 5 seconds
        self._move_arm_safe(target, duration=1.0, hold_time=5.0)
        
        # Close hand after
        self.hands.close_hand('r')

    def action_wedding_toast(self):
        print("[MOTION] Raising glass for toast...")
        
        # 1. Close hand (Hold Glass)
        self.hands.close_hand('r')
        time.sleep(0.5)
        
        # 2. Raise Right Arm
        # User Provided "Wedding Toast" Pose
        # [-1.18, -0.28, -0.10, 0.71, 0.26, -0.12, -0.14]
        
        raise_target = [None] * 17
        raise_target[7] = -1.18
        raise_target[8] = -0.28
        raise_target[9] = -0.10
        raise_target[10] = 0.71
        raise_target[11] = 0.26
        raise_target[12] = -0.12
        raise_target[13] = -0.14
        
        # To speak during hold, start thread
        def speak_toast():
            time.sleep(1.5) # Wait for arm to go up
            mouth.speak("Mabrouk to the happy couple! May your battery life be long and your connection strong! Cheers!")
             
        threading.Thread(target=speak_toast).start()
        
        # Move up and hold
        self._move_arm_safe(raise_target, duration=1.5, hold_time=5.0)
        
        print("[MOTION] Toast complete.")
