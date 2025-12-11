import pyttsx3

def clean_text(text):
    if not text:
        return ""
    # Remove markdown
    text = text.replace("**", "").replace("__", "").replace("*", "")
    
    # Remove emojis/non-ascii
    try:
        text = text.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        pass
        
    return text

text = "Ah Habibi, that's an easy one! The capital city of Turkey is **Ankara**. Yalla, what else can I tell you?"
cleaned = clean_text(text)

print(f"Original: {text}")
print(f"Cleaned:  {cleaned}")

print("Initializing engine...")
try:
    engine = pyttsx3.init()
    print("Speaking...")
    engine.say(cleaned)
    engine.runAndWait()
    print("Finished.")
except Exception as e:
    print(f"Error: {e}")
