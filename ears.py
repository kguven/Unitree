import speech_recognition as sr

def listen(device_index=None):
    """
    Listens to the microphone and returns the recognized text.
    Returns None if no speech is detected or if there's an error.
    """
    import time
    
    recognizer = sr.Recognizer()
    
    # Adjust for ambient noise if necessary
    try:
        # Determine Source
        from dotenv import load_dotenv
        import os
        load_dotenv()
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
             # Convert device_index to int if it's not None
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
        # Using Google Web Speech API for now (requires internet, but free and easy)
        # For offline, we could use Whisper locally, but that requires more setup/resources.
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
