import ears
import brain
import mouth
import time
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    print("------------------------------------------------")
    print("Habibot Voice Interaction Loop")
    print("------------------------------------------------")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("CRITICAL WARNING: GEMINI_API_KEY is missing in .env file.")
        print("Please add your API key to continue.")
        return

    # Initialize ASR once at startup
    print("\n[Init] Initializing Unitree ASR...")
    asr_ready = ears.initialize_asr()
    
    if asr_ready:
        print("[Init] ASR initialized successfully. Wake word: 'My Boss'")
    else:
        print("[Init] ASR not available. Using fallback audio input.")
    
    # Initial greeting
    mouth.speak("System ready. Say My Boss to activate me.")
    
    while True:
        try:
            # 1. Wait for Wake Word
            print("\n[State] Waiting for wake word 'My Boss'...")
            
            wake_word_detected = False
            while not wake_word_detected:
                text = ears.listen()
                
                if text:
                    text_lower = text.lower()
                    if "my boss" in text_lower:
                        print(f"[Wake] Detected in: '{text}'")
                        wake_word_detected = True
                        mouth.speak("Habibot is listening.")
                    else:
                        print(f"[Wake] Ignoring: '{text}'")
                
                time.sleep(0.1)

            # 2. Listen for Command/Question
            print("\n[State] Listening for command...")
            user_input = ears.listen()
            
            if not user_input:
                print("[State] No command received. Returning to wake word.")
                continue
            
            # Check for exit command
            if user_input.lower() in ["exit", "quit", "stop", "bye", "goodbye"]:
                mouth.speak("Goodbye!")
                break

            # 3. Think (Process with Gemini)
            print(f"\n[State] Thinking about: {user_input}")
            start_think = time.time()
            response = brain.think(user_input)
            end_think = time.time()
            print(f"[Timing] Thinking: {end_think - start_think:.2f}s")
            print(f"[Response] {response}")
            
            # 4. Speak Response
            print("\n[State] Speaking...")
            start_speak = time.time()
            mouth.speak(response)
            end_speak = time.time()
            print(f"[Timing] Speaking: {end_speak - start_speak:.2f}s")
            
            # Loop back to wake word detection
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            mouth.speak("Shutting down. Goodbye!")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)

if __name__ == "__main__":
    main()
