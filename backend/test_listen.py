#!/usr/bin/env python3
"""
Test script for Unitree ASR listening functionality.
This script continuously listens and prints what it hears.
"""

import ears
import time

def main():
    print("=" * 60)
    print("Unitree ASR Listening Test")
    print("=" * 60)
    print()
    
    # Initialize ASR
    print("[1/2] Initializing ASR...")
    if not ears.initialize_asr():
        print("FAILED: Could not initialize ASR.")
        print("Make sure you're running on the robot with RUN_ON_ROBOT=True")
        return
    
    print("SUCCESS: ASR initialized.")
    print()
    print("[2/2] Starting continuous listening...")
    print("Speak to the robot. Press Ctrl+C to stop.")
    print("-" * 60)
    print()
    
    try:
        count = 0
        while True:
            # Listen with 30 second timeout
            text = ears.listen(timeout=30)
            
            if text:
                count += 1
                print(f"[{count}] Heard: '{text}'")
                print()
            else:
                print("[Timeout] No speech detected in last 30 seconds.")
                print()
            
            # Small delay
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print()
        print("-" * 60)
        print(f"Test completed. Total phrases heard: {count}")
        print("Exiting...")

if __name__ == "__main__":
    main()
