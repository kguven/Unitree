import pyttsx3
import time

print("Initializing offline TTS engine...")
try:
    engine = pyttsx3.init()
    print("Speaking: 'Testing offline text to speech system.'")
    engine.say("Testing offline text to speech system.")
    engine.runAndWait()
    print("Speech complete.")
except Exception as e:
    print(f"Error: {e}")
