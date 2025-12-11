import sys
import time
import os

# Try to import Unitree SDK
try:
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
except ImportError:
    print("Error: unitree_sdk2py not found. Please ensure the Unitree SDK is installed.")
    print("This script is intended to run on the Unitree robot hardware.")
    sys.exit(1)

def main():
    # Network interface - usually eth0 on the robot, can be adjusted
    # If this fails, try checking 'ifconfig' or 'ip a' on the robot to see the active interface
    network_interface = "eth0" 
    
    print(f"Initializing Unitree SDK2 on {network_interface}...")
    
    # Initialize the channel factory
    # 0 = Domain ID (default), network_interface
    ChannelFactoryInitialize(0, network_interface)
    
    # Create the audio client
    client = AudioClient()
    client.SetTimeout(10.0)
    client.Init()
    
    print("AudioClient initialized.")
    
    # The text to speak
    # "Hello ım Habibot" -> "Hello, I'm Habibot" to sound natural
    text = "Hello, I'm Habibot." 
    print(f"Sending TTS command: '{text}'")
    
    # TtsMaker(text, strategy)
    # Strategy 0 appears to be the standard usage for G1
    ret = client.TtsMaker(text, 0)
    
    print(f"Command sent. Return code: {ret}")

if __name__ == "__main__":
    main()
