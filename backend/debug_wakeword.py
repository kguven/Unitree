import os
from pvrecorder import PvRecorder
import pvporcupine
from dotenv import load_dotenv

def debug_wakeword():
    load_dotenv()
    
    print("--- Audio Device Debug Info ---")
    devices = PvRecorder.get_available_devices()
    print(f"Found {len(devices)} devices:")
    for i, device in enumerate(devices):
        print(f"Index {i}: {device}")
        
    print("\n--- Testing Initialization ---")
    access_key = os.getenv("PORCUPINE_ACCESS_KEY")
    keyword_path = os.getenv("WAKE_WORD_PATH")
    mic_index_env = os.getenv("MIC_DEVICE_INDEX")
    
    print(f"Access Key Present: {bool(access_key)}")
    print(f"Keyword Path: {keyword_path}")
    print(f"Env Mic Index: {mic_index_env}")
    
    if not access_key:
        print("ERROR: No Access Key found!")
        return

    try:
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[keyword_path] if keyword_path else None,
            keywords=['porcupine'] if not keyword_path else None
        )
        print(f"Porcupine initialized. Frame length: {porcupine.frame_length}")
    except Exception as e:
        print(f"Failed to init Porcupine: {e}")
        return

    # Test 1: Default Device
    print("\nTest 1: Initialize PvRecorder with default device (index -1)")
    try:
        recorder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
        print("SUCCESS: Initialized with default device")
        print(f"Selected Device: {recorder.selected_device}")
        recorder.delete()
    except Exception as e:
        print(f"FAILED: {e}")

    # Test 2: Env Device
    if mic_index_env is not None and mic_index_env != "":
        idx = int(mic_index_env)
        print(f"\nTest 2: Initialize PvRecorder with env device (index {idx})")
        try:
            recorder = PvRecorder(device_index=idx, frame_length=porcupine.frame_length)
            print(f"SUCCESS: Initialized with index {idx}")
            print(f"Selected Device: {recorder.selected_device}")
            recorder.delete()
        except Exception as e:
            print(f"FAILED: {e}")

    porcupine.delete()

if __name__ == "__main__":
    debug_wakeword()
