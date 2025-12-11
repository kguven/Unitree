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
# Determine voice inside speak function to allow changing it dynamically if needed
VOICE = "en-US-AriaNeural" 
USE_ONLINE_TTS = False # Set to False to disable edge-tts (fixes delay if network is failing) 

# Robot Configuration
from dotenv import load_dotenv
load_dotenv()
RUN_ON_ROBOT = os.getenv("RUN_ON_ROBOT", "False").lower() == "true"
ROBOT_IFACE = os.getenv("ROBOT_NETWORK_INTERFACE", "eth0")

robot_audio_client = None

if RUN_ON_ROBOT:
    try:
        print(f"[Robot] Initializing Unitree SDK2 on {ROBOT_IFACE}...")
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize
        from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
        
        try:
            ChannelFactoryInitialize(0, ROBOT_IFACE)
            print("[Robot] ChannelFactory initialized.")
        except Exception as e:
            # ChannelFactory might already be initialized by unitree_ears.py
            print(f"[Robot] ChannelFactory init (may already be initialized): {e}")
        
        robot_audio_client = AudioClient()
        robot_audio_client.SetTimeout(10.0)
        robot_audio_client.Init()
        print("[Robot] AudioClient initialized successfully.")
    except ImportError:
        print("[Robot] Error: unitree_sdk2py not found. Please install the SDK.")
        robot_audio_client = None
    except Exception as e:
        print(f"[Robot] Error initializing AudioClient: {e}")
        robot_audio_client = None

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

    # 1. Robot Mode (Priority)
    if RUN_ON_ROBOT and robot_audio_client:
        try:
            print(f"[Robot TTS] Speaking: {text}")
            # TtsMaker(text, strategy). 0 might be default strategy? Example used 0.
            robot_audio_client.TtsMaker(text, 1)
            return
        except Exception as e:
            print(f"[Robot TTS] Error: {e}. Falling back to local methods.")

    # 2. Local Offline Mode (Forced)
    output_file = "temp_speech.mp3"
    
    if not USE_ONLINE_TTS:
        speak_offline(text)
        return

    # 3. Local Online Mode (Edge TTS)
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
