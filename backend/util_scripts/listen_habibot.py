import ears
import time
import sys

def main():
    print("------------------------------------------------")
    print("Habibot Listening Test")
    print("------------------------------------------------")
    print("This script will continuously listen and print what it hears.")
    print("Press Ctrl+C to exit.")
    print("------------------------------------------------")

    while True:
        try:
            print("\n[State] Listening...")
            # ears.listen() handles hardware selection (Unitree vs Mic) internally
            text = ears.listen()
            
            if text:
                print(f"--> I heard: '{text}'")
            else:
                print("--> I heard nothing.")
            
            # small pause to read output
            time.sleep(0.5)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
