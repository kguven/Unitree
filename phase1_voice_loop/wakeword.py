import pvporcupine
from pvrecorder import PvRecorder
import os
import struct

class WakeWordEngine:
    def __init__(self, access_key, keyword_path, device_index=None):
        self.access_key = access_key
        self.keyword_path = keyword_path
        self.device_index = int(device_index) if device_index is not None else -1
        
        self.porcupine = None
        self.recorder = None
        
        self._init_porcupine()

    def _init_porcupine(self):
        try:
            # Check if keyword path exists as a file
            if os.path.exists(self.keyword_path):
                print(f"Loading wake word from file: {self.keyword_path}")
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=[self.keyword_path]
                )
            else:
                # Assume it's a built-in keyword (e.g. "porcupine", "bumblebee")
                print(f"Wake word file not found at '{self.keyword_path}'. Using as built-in keyword.")
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=[self.keyword_path],
                    sensitivities=[0.7] # Increase sensitivity
                )
            
            # If device_index is -1, PvRecorder uses default
            try:
                self.recorder = PvRecorder(
                    device_index=self.device_index,
                    frame_length=self.porcupine.frame_length
                )
            except Exception as e:
                print(f"Error initializing PvRecorder with device_index={self.device_index}: {e}")
                print("Available devices:")
                for i, device in enumerate(PvRecorder.get_available_devices()):
                    print(f"  [{i}] {device}")
                raise e

            print(f"WakeWordEngine initialized. Porcupine version: {self.porcupine.version}")
            print(f"Listening on device: {self.recorder.selected_device}")
            
        except Exception as e:
            # Clean up if partial init happened
            self.cleanup()
            raise RuntimeError(f"Failed to initialize Porcupine: {e}")

    def wait_for_wake_word(self):
        """
        Listens for the wake word.
        Returns True if wake word detected.
        Returns False if interrupted or error.
        """
        if not self.porcupine or not self.recorder:
            print("WakeWordEngine not initialized.")
            return False
            
        try:
            self.recorder.start()
            frame_count = 0
            
            while True:
                pcm = self.recorder.read()
                result = self.porcupine.process(pcm)
                
                # Visual heartbeat
                frame_count += 1
                if frame_count % 10 == 0:
                     print(".", end="", flush=True)

                if result >= 0:
                    print("\nWake Word Detected!")
                    # Wake word detected
                    return True
                    
        except KeyboardInterrupt:
            return False
        except Exception as e:
            print(f"Error in wake word loop: {e}")
            return False
        finally:
            if self.recorder.is_recording:
                self.recorder.stop()

    def cleanup(self):
        if self.recorder:
            self.recorder.delete()
            self.recorder = None
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None

    def __del__(self):
        self.cleanup()
