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
        # Convert device_index to int if it's not None
        if device_index is not None:
            device_index = int(device_index)
            
        with sr.Microphone(device_index=device_index) as source:
            print(f"Listening on device index {device_index if device_index is not None else 'default'}...")
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
