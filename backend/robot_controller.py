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

    WaistYaw = 12
    WaistRoll = 13        # NOTE: INVALID for g1 23dof/29dof with waist locked
    WaistA = 13           # NOTE: INVALID for g1 23dof/29dof with waist locked
    WaistPitch = 14       # NOTE: INVALID for g1 23dof/29dof with waist locked
    WaistB = 14           # NOTE: INVALID for g1 23dof/29dof with waist locked

    # Left arm
    LeftShoulderPitch = 15
    LeftShoulderRoll = 16
    LeftShoulderYaw = 17
    LeftElbow = 18
    LeftWristRoll = 19
    LeftWristPitch = 20   # NOTE: INVALID for g1 23dof
    LeftWristYaw = 21     # NOTE: INVALID for g1 23dof

    # Right arm
    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbow = 25
    RightWristRoll = 26
    RightWristPitch = 27  # NOTE: INVALID for g1 23dof
    RightWristYaw = 28    # NOTE: INVALID for g1 23dof

    kNotUsedJoint = 29 # NOTE: Weight


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

        # Photo Upload State
        self.photo_active = False
        self.photo_interval = 60 # seconds
        self.photo_url = "http://localhost:5000/upload" # Default URL
        self.photo_thread = None

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
        
        # Phase 1: Speak
        with self.lock:
            mouth.speak(response)

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
        while self.photo_active and self.running:
            try:
                # Capture Photo (Mock)
                print("[Photo] Capturing photo...")
                # In real life, camera capture here.
                # We will create a dummy image byte array (random noise or just text)
                dummy_image = b"FAKE_IMAGE_DATA_" + str(datetime.datetime.now()).encode()
                
                # Upload
                if self.photo_url:
                    print(f"[Photo] Uploading to {self.photo_url}...")
                    try:
                        # Post as multipart/form-data or raw bytes depending on server. 
                        # Standard way: files={'file': ...}
                        files = {'file': ('photo.jpg', dummy_image, 'image/jpeg')}
                        response = requests.post(self.photo_url, files=files, timeout=5)
                        print(f"[Photo] Upload Status: {response.status_code}")
                    except Exception as e:
                        print(f"[Photo] Upload Failed: {e}")
                
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
        print("Photo loop stopped.")

    # --- SAFE ARM CONTROL ---
    
    def _move_arm_safe(self, target_config, duration=3.0, hold_time=0.0):
        """
        Executes a safe arm movement:
        1. Initialize DDS Publisher/Subscriber
        2. Smoothly move from current LowState to Zero
        3. Smoothly move from Zero to Target
        4. HOLD at Target (optional)
        5. Smoothly move from Target to Zero
        6. Release Control
        """
        print("[SafeArm] Initializing DDS...")
        # Note: We assume ChannelFactoryInitialize is called globally or inside here if needed.
        # Ideally it's called once in main.
        try:
            ChannelFactoryInitialize(0)
        except:
            pass # Might already be initialized

        arm_sdk_publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
        arm_sdk_publisher.Init()
        
        lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        
        # Shared state for callback
        state_container = {"low_state": None, "first_update": False}
        
        def low_state_handler(msg: LowState_):
            state_container["low_state"] = msg
            if not state_container["first_update"]:
                state_container["first_update"] = True
                
        lowstate_subscriber.Init(low_state_handler, 10)
        
        # Wait for first state
        print("[SafeArm] Waiting for LowState...")
        wait_start = time.time()
        while not state_container["first_update"]:
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
        # Using the G1JointIndex class we added
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
        
        # target_config should be length 17 (Same as arm_joints list)
        # If user passes less, we pad or ignore, but safety first:
        if len(target_config) < len(arm_joints):
            # Pad with zeros if shorter
            target_config = list(target_config) + [0.0]*(len(arm_joints)-len(target_config))
        
        print(f"[SafeArm] Starting movement loop (Duration={duration}s, Hold={hold_time}s)...")
        
        # Phases
        # 0 to T: Zero Posture
        # T to 3T: Move to Target
        # 3T to 3T+H: Hold
        # 3T+H to 6T+H: Move Back to Zero
        # 6T+H to 7T+H: Release

        total_time = (duration * 7.0) + hold_time
        
        while current_time < total_time:
            start_loop = time.time()
            current_time += control_dt
            
            # --- Logic from Custom.LowCmdWrite ---
            
            if current_time < duration:
                # [Stage 1]: Zero Posture
                low_cmd.motor_cmd[G1JointIndex.kNotUsedJoint].q =  1 # Enable arm_sdk
                for i, joint in enumerate(arm_joints):
                    ratio = np.clip(current_time / duration, 0.0, 1.0)
                    low_cmd.motor_cmd[joint].tau = 0.
                    # Interpolate from current state to 0? verify logic from example
                    # Example: (1.0 - ratio) * self.low_state.motor_state[joint].q
                    # This means it fades FROM current state TO 0.
                    low_cmd.motor_cmd[joint].q = (1.0 - ratio) * state_container["low_state"].motor_state[joint].q
                    low_cmd.motor_cmd[joint].dq = 0.
                    low_cmd.motor_cmd[joint].kp = kp
                    low_cmd.motor_cmd[joint].kd = kd
                    
            elif current_time < duration * 3:
                 # [Stage 2]: Move to Target
                 for i, joint in enumerate(arm_joints):
                    ratio = np.clip((current_time - duration) / (duration * 2), 0.0, 1.0)
                    low_cmd.motor_cmd[joint].tau = 0.
                    # ratio * target + (1-ratio) * current_state(which is 0 now effectively? NO, current q from state)
                    # The example logic: ratio * self.target_pos[i] + (1.0 - ratio) * self.low_state.motor_state[joint].q 
                    # This continuously fights the current state to move towards target. 
                    low_cmd.motor_cmd[joint].q = ratio * target_config[i] + (1.0 - ratio) * state_container["low_state"].motor_state[joint].q
                    low_cmd.motor_cmd[joint].dq = 0.
                    low_cmd.motor_cmd[joint].kp = kp
                    low_cmd.motor_cmd[joint].kd = kd
            
            elif current_time < (duration * 3 + hold_time):
                # [Stage 3]: HOLD
                for i, joint in enumerate(arm_joints):
                    # Maintain target position
                    # We continue to use the logic but with ratio=1.0 relative to target
                    low_cmd.motor_cmd[joint].tau = 0.
                    low_cmd.motor_cmd[joint].q = 1.0 * target_config[i] + 0.0 * state_container["low_state"].motor_state[joint].q
                    low_cmd.motor_cmd[joint].dq = 0
                    low_cmd.motor_cmd[joint].kp = kp
                    low_cmd.motor_cmd[joint].kd = kd
                    
            elif current_time < (duration * 6 + hold_time):
                # [Stage 4]: Back to Zero
                for i, joint in enumerate(arm_joints):
                    ratio = np.clip((current_time - (duration * 3 + hold_time)) / (duration * 3), 0.0, 1.0)
                    low_cmd.motor_cmd[joint].tau = 0.
                    # Fading out to 0 again?
                    # Example says: (1.0 - ratio) * self.low_state.motor_state[joint].q
                    # Yes, simply reduce gain/target to 0 relative to current state.
                    low_cmd.motor_cmd[joint].q = (1.0 - ratio) * state_container["low_state"].motor_state[joint].q
                    low_cmd.motor_cmd[joint].dq = 0.
                    low_cmd.motor_cmd[joint].kp = kp
                    low_cmd.motor_cmd[joint].kd = kd

            elif current_time < (duration * 7 + hold_time):
                 # [Stage 5]: Release
                 for i, joint in enumerate(arm_joints):
                    ratio = np.clip((current_time - (duration * 6 + hold_time)) / duration, 0.0, 1.0)
                    low_cmd.motor_cmd[G1JointIndex.kNotUsedJoint].q = (1 - ratio) # Disable bit fading
            
            # Write Command
            low_cmd.crc = crc_util.Crc(low_cmd)
            arm_sdk_publisher.Write(low_cmd)
            
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
        # We need 17 values. 
        # Right Arm starts at index 7: R_Pitch, R_Roll, R_Yaw, R_Elbow, R_WristRoll, R_WristPitch, R_WristYaw
        # Let's target: Right Shoulder Pitch=0, Roll=0, Yaw=0, Elbow=-1.5 (bent?), Wrist...
        # Just a simple forward reach: RightShoulderPitch = -1.0 approx?
        
        # Poses from example:
        # 0., kPi_2,  0., kPi_2, 0., 0., 0., (Left)
        # 0., -kPi_2, 0., kPi_2, 0., 0., 0., (Right)
        
        target = [0.0] * 17
        # Right Arm Extend (Custom)
        # RightShoulderPitch
        target[7] = -1.0 # Lift arm?
        target[10] = 1.0 # Elbow bend
        
        # Open Hand
        self.hands.open_hand('r')
        
        self._move_arm_safe(target, duration=1.5)
        
        time.sleep(1)
        print("[MOTION] Pulling arm back quickly!")
        mouth.speak("Ah! Too slow! Just kidding, here you go.")
        
        # Close hand maybe?
        self.hands.close_hand('r')
        
        # Another move? Maybe just return. 
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
        target = [0.0] * 17
        # Lift both arms
        target[0] = 1.0 # Left Pitch
        target[7] = -1.0 # Right Pitch
        
        self.hands.open_hand('both')
        self._move_arm_safe(target, duration=2.0) # Will lift and lower
        print("[MOTION] Bobbing Head + Arm Wave")

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
        print("[MOTION] Shrug Shoulders")
        
        # Shrug Gesture: Palms up, elbows in, hands out
        shrug_target = [0.0] * 17
        # Left Arm
        shrug_target[1] = 0.5   # Left Shoulder Roll (Out)
        shrug_target[3] = 0.5   # Left Elbow (Slight Bend)
        shrug_target[4] = 1.5   # Left Wrist Roll (Palm Up)
        
        # Right Arm
        shrug_target[8] = -0.5  # Right Shoulder Roll (Out)
        shrug_target[10] = 0.5  # Right Elbow (Slight Bend)
        shrug_target[11] = -1.5 # Right Wrist Roll (Palm Up)
        
        self.hands.open_hand('both')
        self._move_arm_safe(shrug_target, duration=1.0, hold_time=2.0)

        print("[AUDIO] Ba Dum Tss")
        
        # Restore/Run Custom Routine
        try:
            ChannelFactoryInitialize(0, "eth0")
        except:
            pass
        try:
            custom_runner = custom.Custom()
            custom_runner.Init()
            custom_runner.Start()
        except Exception as e:
            print(f"Custom routine error: {e}")

    def action_living_statue(self):
        print("[MOTION] FREEZE MODE (Damping)")
        time.sleep(3)
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
        
        # Target: Raise Left Arm
        target = [0.0] * 17
        target[0] = -1.2  # Left Shoulder Pitch (Up)
        target[3] = 1.2   # Left Elbow (Bent)
        target[4] = -0.5  # Left Wrist Roll
        
        # Peace Sign
        self.hands.gesture('l', 'peace')
        print("[MOTION] Tilt Head") # (No hardware control for head tilt yet)
        
        # Execute Move and Hold
        self._move_arm_safe(target, duration=1.5, hold_time=4.0)
        
        mouth.speak("Send me that on Instagram! I look great.")
        # Reset Hand
        self.hands.open_hand('l')

    def action_rps_game(self):
        # Swing Target: Lift arm with bent elbow
        swing_target = [0.0] * 17
        swing_target[7] = -0.8  # Right Shoulder Pitch (Lift)
        swing_target[10] = 1.5  # Right Elbow (Bent)
        
        # Swing 1
        mouth.speak("Rock...")
        print("[MOTION] Swing Arm 1...")
        self.hands.close_hand('r') # Fist during windup
        self._move_arm_safe(swing_target, duration=0.8)
        
        # Swing 2
        mouth.speak("Paper...")
        print("[MOTION] Swing Arm 2...")
        self._move_arm_safe(swing_target, duration=0.8)
        
        # Swing 3
        mouth.speak("Scissors...")
        print("[MOTION] Swing Arm 3...")
        self._move_arm_safe(swing_target, duration=0.8)
        
        # SHOOT
        mouth.speak("SHOOT!")
        choice = random.choice(["rock", "paper", "scissors"])
        print(f"[MOTION] Hand Pose: {choice}")
        
        # Move arm forward to show
        show_target = [0.0] * 17
        show_target[7] = -0.5
        show_target[10] = 0.5 # Less bent, extending
        
        # We want to hold it a bit? _move_arm_safe returns to zero.
        # Let's just do a normal safe move but show the hand gesture during it.
        
        def set_hand():
            time.sleep(0.5) # Wait for arm to be in position
            self.hands.gesture('r', choice)
            
        threading.Thread(target=set_hand).start()
        
        self._move_arm_safe(show_target, duration=2.0)
        
        mouth.speak(f"I chose {choice}!")
        time.sleep(1.0)
        self.hands.open_hand('r') # Reset hand

    def action_the_butler(self):
        print("[MOTION] Butler Pose (Tray)...")
        mouth.speak("Please, take one. I cannot eat, I am on a diet of pure lithium.")
        
        # Target: Right Arm "L" Shape (Tray)
        target = [0.0] * 17
        target[7] = 0.0   # Right Shoulder Pitch (Neutral)
        target[8] = 0.0   # Right Shoulder Roll (Neutral)
        target[9] = 0.0   # Right Shoulder Yaw (Neutral
        target[10] = 1.6  # Right Elbow (Bent 90 deg)
        target[11] = 1.57 # Right Wrist Roll (Rotate for palm up)
        
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
        # Shoulder Pitch -1.3 (Up), Elbow 1.5 (Bent)
        raise_target = [0.0] * 17
        raise_target[7] = -1.3
        raise_target[10] = 1.5
        
        # Move up
        self._move_arm_safe(raise_target, duration=1.5, hold_time=4.0)
        
        # Note: _move_arm_safe blocks during the move and hold.
        # But we want to speak *while* holding or *after* raising?
        # The current implementation of _move_arm_safe blocks. 
        # So we can't speak "during" the hold easily unless we thread it 
        # or if we split the move.
        # _move_arm_safe does Zero->Target->Hold->Zero.
        # Ideally, we speak during the Hold phase.
        
        # To fix this properly, let's use a thread for speaking since _move_arm_safe is blocking.
        def speak_toast():
            time.sleep(1.5) # Wait for arm to go up
            mouth.speak("Mabrouk to the happy couple! May your battery life be long and your connection strong! Cheers!")
             
        threading.Thread(target=speak_toast).start()
        
        # The arm will hold for 4 seconds (covering the speech) then lower.
        
        print("[MOTION] Toast complete.")
