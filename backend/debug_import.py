
import sys
import traceback

print(f"Python: {sys.executable}")
print(f"Path: {sys.path}")

try:
    print("Attempting to import unitree_sdk2py...")
    import unitree_sdk2py
    print(f"Success! {unitree_sdk2py}")
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.go2.video.video_client import VideoClient
    print("Classes imported.")
except Exception:
    traceback.print_exc()
