import pvporcupine
from pvrecorder import PvRecorder
import os
from dotenv import load_dotenv

load_dotenv()

def test_builtin_keyword():
    access_key = os.getenv("PORCUPINE_ACCESS_KEY")
    device_index = int(os.getenv("MIC_DEVICE_INDEX", -1))
    
    print(f"Testing with built-in keyword 'porcupine' on device index {device_index}...")

    try:
        # Use 'keywords' argument for built-ins instead of 'keyword_paths'
        porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=['porcupine'] 
        )
        
        recorder = PvRecorder(
            device_index=device_index,
            frame_length=porcupine.frame_length
        )
        recorder.start()
        
        print("Listening for 'Porcupine'... (Press Ctrl+C to stop)")
        
        while True:
            pcm = recorder.read()
            result = porcupine.process(pcm)
            if result >= 0:
                print("Wake Word 'Porcupine' Detected!")
                
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if 'recorder' in locals():
            recorder.delete()
        if 'porcupine' in locals():
            porcupine.delete()

if __name__ == "__main__":
    test_builtin_keyword()
