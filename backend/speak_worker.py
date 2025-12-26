import pyttsx3
import sys
import os

def speak():
    try:
        # Read text from file to avoid CLI escaping issues
        if not os.path.exists("temp_tts_text.txt"):
            return

        with open("temp_tts_text.txt", "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            return

        print(f"[Worker] Speaking: {text}")
        engine = pyttsx3.init()
        engine.setProperty('rate', 150) # Optional: Adjust speed
        engine.say(text)
        engine.runAndWait()
        print("[Worker] Finished.")
        
    except Exception as e:
        print(f"[Worker] Error: {e}")

if __name__ == "__main__":
    speak()
