import sys
import asyncio
import edge_tts
import pygame
import os

# Voice options:
# en-US-GuyNeural (Male)
# en-US-AriaNeural (Female)
# Let's stick to a clear English voice for now, maybe with a specific pitch/rate to sound unique.
# Determine voice inside speak function to allow changing it dynamically if needed
VOICE = "en-US-AriaNeural" 
USE_ONLINE_TTS = False # Set to False to disable edge-tts (fixes delay if network is failing) 

# Initialize offline TTS engine globally to avoid threading issues
try:
    import pyttsx3
    offline_engine = pyttsx3.init()
except Exception as e:
    print(f"Warning: pyttsx3 not available: {e}")
    offline_engine = None

async def generate_audio(text, output_file="response.mp3"):
    """
    Generates audio from text using edge-tts.
    """
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def play_audio(file_path="response.mp3", device_name=None):
    """
    Plays the audio file using pygame.
    """
    try:
        # Initialize mixer with specific device if provided
        # Note: devicename argument requires pygame 2.0+ and SDL2
        if device_name:
            try:
                pygame.mixer.init(devicename=device_name)
            except Exception as e:
                print(f"Warning: Could not initialize mixer with device '{device_name}': {e}")
                print("Falling back to default device.")
                pygame.mixer.init()
        else:
            pygame.mixer.init()

        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        pygame.mixer.quit() # Release the file so it can be overwritten
        
    except pygame.error as e:
        if "Device busy" in str(e):
            print("Audio device busy, retrying in 1 second...")
            import time
            time.sleep(1)
            play_audio(file_path, device_name) # Retry
        else:
             print(f"Pygame error playing audio: {e}")
    except Exception as e:
        # Check if file exists to distinguish error type
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file {file_path} not found.")
        else:
            raise e # Re-raise to trigger fallback

def speak_offline(text):
    """
    Fallback TTS using pyttsx3 (offline) via separate process to avoid conflicts.
    """
    import subprocess
    
    try:
        # Write text to temp file
        with open("temp_tts_text.txt", "w", encoding="utf-8") as f:
            f.write(text)
            
        # Call worker script
        # Using sys.executable ensures we use the same python interpreter
        result = subprocess.run([sys.executable, "speak_worker.py"], capture_output=True, text=True)
        
        # Isolate logs
        print(result.stdout)
        if result.stderr:
            print(f"[Worker Error] {result.stderr}")
            
    except Exception as e:
         print(f"Error in speak_offline (subprocess): {e}")

def clean_text(text):
    """
    Removes markdown formatting (bold, italic) that might confuse TTS.
    """
    if not text:
        return ""
    # Remove markdown
    text = text.replace("**", "").replace("__", "").replace("*", "")
    
    # Remove emojis/non-ascii (pyttsx3 struggle with them)
    try:
        text = text.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        pass
        
    return text

def speak(text, device_name=None):
    """
    Main function to handle TTS and playback.
    """
    if not text:
        return

    # Clean the text
    text = clean_text(text)

    output_file = "temp_speech.mp3"
    
    if not USE_ONLINE_TTS:
        speak_offline(text)
        return

    try:
        # Generate online execution
        asyncio.run(generate_audio(text, output_file))
        
        # Verify file is not empty
        if not os.path.exists(output_file) or os.path.getsize(output_file) < 100:
             raise ValueError("Generated audio file is too small or missing.")

        play_audio(output_file, device_name)
    except Exception as e:
        print(f"Error in speak (edge_tts): {e}")
        print("Switching to offline TTS fallback...")
        speak_offline(text)

if __name__ == "__main__":
    speak("Hello habibi, I am ready to talk.")
