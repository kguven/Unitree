import ears
import brain
import mouth
import time
import os
from dotenv import load_dotenv
from wakeword import WakeWordEngine

def main():
    load_dotenv()
    
    print("------------------------------------------------")
    print("Habibot Voice Interaction Loop (Phase 2)")
    print("------------------------------------------------")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("CRITICAL WARNING: GEMINI_API_KEY is missing in .env file.")
        print("Please add your API key to continue.")
        return

    # Load hardware config
    porcupine_key = os.getenv("PORCUPINE_ACCESS_KEY")
    wake_word_path = os.getenv("WAKE_WORD_PATH")
    mic_index = os.getenv("MIC_DEVICE_INDEX")
    if mic_index == "":
        mic_index = None

    # Resolve Speaker Device
    speaker_index = os.getenv("SPEAKER_DEVICE_INDEX")
    speaker_name = None
    if speaker_index:
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            dev_info = p.get_device_info_by_host_api_device_index(0, int(speaker_index))
            speaker_name = dev_info.get('name')
            p.terminate()
            print(f"Initialized Speaker: {speaker_name} (Index: {speaker_index})")
        except Exception as e:
            print(f"Warning: Could not resolve speaker index {speaker_index}: {e}")
            speaker_name = None

    # Initialize Wake Word Engine
    # We are using ASR-based wake word now. "Hey Habibot" or "Habibot"
    print("\n[Init] Using ASR-based Wake Word: 'Hey Habibot'")
    mouth.speak("System ready. Say Hey Habibot.", device_name=speaker_name)
    
    while True:
        try:
            # 0. Wait for Wake Word (ASR Loop)
            print("\n[State] Waiting for 'Hey Habibot'...")
            
            # Listen indefinitely until keyword match
            wake_word_detected = False
            while not wake_word_detected:
                # listen() uses Unitree ASR if available (configured in ears.py/env)
                text = ears.listen()
                
                if text:
                    text_lower = text.lower()
                    # Check for keywords - Only 'hey my bot' (or close variations if needed)
                    if "hey my bot" in text_lower or "hey, my bot" in text_lower:
                        print(f"Wake word detected in: '{text}'")
                        wake_word_detected = True
                        mouth.speak("Yeah?", device_name=speaker_name)
                    else:
                        print(f"Ignoring: '{text}'")
                
                # Small sleep to prevent tight loop if listen returns None immediately
                time.sleep(0.1)

            # 1. Listen for Command
            print("\n[State] Listening for command...")
            # We can reuse ears.listen() or just continue if the wake word phrase contained the command
            # For natural flow, let's listen again for the actual command explicitly
            # or check if the wake word sentence had more content.
            
            # Simple approach: Listen again
            user_input = ears.listen()
            
            if user_input:
                # Check for exit command
                if user_input.lower() in ["exit", "quit", "stop", "bye"]:
                    mouth.speak("Goodbye habibi!", device_name=speaker_name)
                    break

                # 2. Think
                print("\n[State] Thinking...")
                start_think = time.time()
                response = brain.think(user_input)
                end_think = time.time()
                print(f"[Timing] Thinking: {end_think - start_think:.2f}s")
                print(f"Habibot: {response}")
                
                # 3. Speak
                print("\n[State] Speaking...")
                start_speak = time.time()
                mouth.speak(response, device_name=speaker_name)
                end_speak = time.time()
                print(f"[Timing] Speaking: {end_speak - start_speak:.2f}s")
            
            # Small delay to prevent tight loop if listen returns immediately
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
