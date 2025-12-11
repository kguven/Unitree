import ears
import time

def main():
    print("------------------------------------------------")
    print("Habibot ASR Wake Word Test")
    print("------------------------------------------------")
    print("Listening for: 'Hey Habibot', 'Habibot', 'Robot'")
    print("------------------------------------------------")

    # Ensure Unitree ASR is enabled (usually default via env or ears.py logic)
    # You can verify this by checking if [UnitreeASR] logs appear.

    while True:
        try:
            print("\n[State] Waiting for keyword...")
            text = ears.listen()
            
            if text:
                text_lower = text.lower()
                print(f"--> Heard: '{text}'")
                
                if "my boss" in text_lower:
                    print(">>> WAKE WORD DETECTED! <<<")
                else:
                    print("... ignored (no keyword)")
            
            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
