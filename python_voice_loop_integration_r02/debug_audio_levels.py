import os
import struct
import math
from pvrecorder import PvRecorder
from dotenv import load_dotenv
import time

load_dotenv()

def debug_audio_levels():
    device_index = int(os.getenv("MIC_DEVICE_INDEX", -1))
    print(f"Debug: Using Mic Device Index: {device_index}")
    
    try:
        recorder = PvRecorder(device_index=device_index, frame_length=512)
        print(f"Selected Device: {recorder.selected_device}")
        
        recorder.start()
        print("Recording... (Press Ctrl+C to stop)")
        print("Please speak into the microphone to check levels.")

        while True:
            pcm = recorder.read()
            # Calculate RMS (Root Mean Square) for volume
            rms = math.sqrt(sum(x * x for x in pcm) / len(pcm))
            
            # Simple visualization
            bars = "#" * int(rms / 100)
            print(f"Level: {int(rms):5d} | {bars}", end="\r")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if 'recorder' in locals():
            recorder.delete()

if __name__ == "__main__":
    debug_audio_levels()
