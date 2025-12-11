import speech_recognition as sr
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Global ASR subscriber instance
_asr_subscriber = None
_asr_initialized = False

def initialize_asr():
    """
    Initialize the Unitree ASR subscriber once at startup.
    Returns True if successful, False otherwise.
    """
    global _asr_subscriber, _asr_initialized
    
    if _asr_initialized:
        print("[Ears] ASR already initialized.")
        return True
    
    RUN_ON_ROBOT = os.getenv("RUN_ON_ROBOT", "False").lower() == "true"
    USE_BUILTIN_ASR = os.getenv("USE_UNITREE_ASR", "True").lower() == "true"
    
    if not RUN_ON_ROBOT or not USE_BUILTIN_ASR:
        print("[Ears] ASR not enabled (RUN_ON_ROBOT or USE_UNITREE_ASR is False)")
        return False
    
    try:
        from unitree_ears import UnitreeASRSubscriber
        _asr_subscriber = UnitreeASRSubscriber()
        _asr_subscriber.start()
        _asr_initialized = True
        print("[Ears] ASR initialized successfully.")
        return True
    except ImportError:
        print("[Ears] Unitree ASR not found.")
        return False
    except Exception as e:
        print(f"[Ears] Error initializing ASR: {e}")
        return False

def listen_asr(timeout=10):
    """
    Poll the ASR subscriber for new text.
    Returns recognized text or None if timeout.
    """
    global _asr_subscriber
    
    if not _asr_subscriber:
        print("[Ears] ASR not initialized. Call initialize_asr() first.")
        return None
    
    print("[Ears] Waiting for ASR...")
    start_wait = time.time()
    
    while (time.time() - start_wait) < timeout:
        text = _asr_subscriber.get_last_text()
        if text:
            print(f"[Ears] ASR Received: {text}")
            return text
        time.sleep(0.1)
    
    print("[Ears] ASR Timeout.")
    return None

def listen(device_index=None):
    """
    Listens to the microphone and returns the recognized text.
    If ASR is initialized, uses ASR. Otherwise falls back to microphone.
    Returns None if no speech is detected or if there's an error.
    """
    global _asr_subscriber
    
    # If ASR is available, use it
    if _asr_subscriber:
        return listen_asr()
    
    # Fallback to traditional microphone input
    recognizer = sr.Recognizer()
    
    try:
        RUN_ON_ROBOT = os.getenv("RUN_ON_ROBOT", "False").lower() == "true"
        
        source = None
        if RUN_ON_ROBOT:
            try:
                from unitree_ears import UnitreeAudioSource
                source = UnitreeAudioSource()
                print("[Ears] Using Unitree Multicast Audio Source.")
            except ImportError:
                print("[Ears] Unitree audio source not found, falling back to mic.")

        if source is None:
            if device_index is not None:
                device_index = int(device_index)
            source = sr.Microphone(device_index=device_index)
            print(f"Listening on device index {device_index if device_index is not None else 'default'}...")

        with source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                start_listen = time.time()
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                end_listen = time.time()
                print(f"[Timing] Audio Capture: {end_listen - start_listen:.2f}s")
            except sr.WaitTimeoutError:
                print("Timeout: No speech detected.")
                return None
    except OSError as e:
        print(f"Error accessing microphone (device index {device_index}): {e}")
        return None

    try:
        print("Recognizing...")
        start_recog = time.time()
        text = recognizer.recognize_google(audio)
        end_recog = time.time()
        print(f"[Timing] Recognition: {end_recog - start_recog:.2f}s")
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return None
    except Exception as e:
        print(f"Error in listen: {e}")
        return None

if __name__ == "__main__":
    # Test the listen function
    listen()
