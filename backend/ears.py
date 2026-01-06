import time
import os
from dotenv import load_dotenv
from . import unitree_ears

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
    
    try:
        _asr_subscriber = unitree_ears.UnitreeASRSubscriber()
        _asr_subscriber.start()
        _asr_initialized = True
        print("[Ears] ASR initialized successfully.")
        return True
    except ImportError:
        print("[Ears] ERROR: Unitree ASR not found. Cannot proceed.")
        return False
    except Exception as e:
        print(f"[Ears] ERROR: Failed to initialize ASR: {e}")
        return False

def listen(timeout=10):
    """
    Poll the ASR subscriber for new text.
    Returns recognized text or None if timeout.
    """
    global _asr_subscriber
    
    if not _asr_subscriber:
        print("[Ears] ERROR: ASR not initialized. Call initialize_asr() first.")
        time.sleep(5)
        return None
    
    start_wait = time.time()
    
    while (time.time() - start_wait) < timeout:
        text = _asr_subscriber.get_last_text()
        if text:
            print(f"[Ears] ASR: {text}")
            return text
        time.sleep(0.1)
    
    # Timeout - no text received
    return None

def check_latest():
    """
    Check for the latest text immediately without blocking/timeout.
    Returns the text if available safely, else None.
    """
    global _asr_subscriber
    
    if not _asr_subscriber:
        return None
        
    return _asr_subscriber.get_last_text()

if __name__ == "__main__":
    # Test the ASR
    if initialize_asr():
        print("Listening for 30 seconds...")
        result = listen(timeout=30)
        if result:
            print(f"Result: {result}")
        else:
            print("No speech detected.")
    else:
        print("Failed to initialize ASR.")
