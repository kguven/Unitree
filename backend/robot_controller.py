import threading
import time
import random
import os
from . import ears
from . import mouth
from . import brain
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import action_map
from dataclasses import dataclass
from . import custom


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

    # --- ACTION SCRIPTS ---
    # (Same as before, abbreviated for brevity where possible, but keeping full mocked logic)

    def action_the_giver(self):
        print("[MOTION] Extending Right Arm with card...")
        mouth.speak("Here is my card... take it!")
        time.sleep(2)
        print("[MOTION] Pulling arm back quickly!")
        mouth.speak("Ah! Too slow! Just kidding, here you go.")
        print("[MOTION] Extending arm again...")

        try:
            ChannelFactoryInitialize(0, "eth0")
            armAction_client = G1ArmActionClient()  
            armAction_client.SetTimeout(10.0)
            armAction_client.Init()
            armAction_client.ExecuteAction(action_map.get("two-hand kiss"))
        except Exception as e:
            print(f"Arm action failed: {e}")
        time.sleep(1)

    def action_robot_sings(self):
        mouth.speak("This next song is dedicated to the beautiful couple! Yalla!")
        print("[AUDIO] Playing MP3: Nancy Ajram...")
        time.sleep(5)
        print("[MOTION] Bobbing Head + Arm Wave")

    def action_standup_comedy(self):
        prompt = "You are a Lebanese comedian. Tell a short, funny, sarcastic joke about traffic in Beirut or marriage."
        joke = brain.think(prompt)
        mouth.speak(joke)
        print("[MOTION] Shrug Shoulders")
        print("[AUDIO] Ba Dum Tss")
        ChannelFactoryInitialize(0, "eth0")
        custom_runner = custom.Custom()
        custom_runner.Init()
        custom_runner.Start()

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
        print("[MOTION] Tilt Head")
        time.sleep(5)
        mouth.speak("Send me that on Instagram! I look great.")

    def action_rps_game(self):
        mouth.speak("Rock... Paper... Scissors... SHOOT!")
        print("[MOTION] Swing Arm 1...")
        time.sleep(0.5)
        print("[MOTION] Swing Arm 2...")
        time.sleep(0.5)
        print("[MOTION] Swing Arm 3...")
        choice = random.choice(["Fist", "Flat", "V-Shape"])
        print(f"[MOTION] Hand Pose: {choice}")
        mouth.speak(f"I chose {choice}!")

    def action_the_butler(self):
        print("[MOTION] Arm to 90-degree 'L' shape.")
        print("[MOTION] Engage Position Lock.")
        mouth.speak("Please, take one. I cannot eat, I am on a diet of pure lithium.")

    def action_wedding_toast(self):
        print("[MOTION] Raise Right Arm (Glass).")
        mouth.speak("Mabrouk to the happy couple! May your battery life be long and your connection strong!")
        print("[MOTION] Cheers gesture.")
