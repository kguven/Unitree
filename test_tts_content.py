import pyttsx3
import time

def clean_text(text):
    return text.replace("**", "").replace("__", "").replace("*", "")

text = "Ah, Italy! Lovely place. The capital city, habibi, is **Rome**."
cleaned = clean_text(text)

print("Initializing engine...")
engine = pyttsx3.init()

print(f"Original: {text}")
print(f"Cleaned:  {cleaned}")

print("Speaking 1 (System Ready)...")
engine.say("System ready.")
engine.runAndWait()
time.sleep(1)

print("Speaking 2 (Answer)...")
engine.say(cleaned)
engine.runAndWait()
print("Finished.")
