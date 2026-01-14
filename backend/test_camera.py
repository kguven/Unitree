import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



def test_camera():
    print("--------------------------------------------------")
    print("Running RealSense Camera Test...")
    print("--------------------------------------------------")
    
    # Try to initialize ChannelFactory (Required for Network Camera)
    try:
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize
        if len(sys.argv) > 1:
            ChannelFactoryInitialize(0, sys.argv[1])
        else:
            ChannelFactoryInitialize(0)
    except ImportError:
        print("SDK not found. Camera might fail if network based.")

    # With Context Manager
    from backend.camera import CameraCapture
    with CameraCapture() as cam:
        if not cam.is_initialized:
            print("FAIL: Camera failed to start.")
            return

        print("PASS: Camera started.")
        print(f"Info: {cam.get_frame_info()}")
        
        print("\n[2] Waiting for auto-exposure stabilization (2s)...")
        time.sleep(2)
        
        print("\n[3] Capturing Frame 1...")
        img1 = cam.capture_frame()
        if img1 is not None:
             print(f"PASS: Frame 1 captured. Shape: {img1.shape}")
             # Save test image
             import cv2
             cv2.imwrite('test_frame_1.jpg', img1)
             print("Saved to test_frame_1.jpg")
        else:
             print("FAIL: Frame 1 capture failed.")

        return # End here for updated test

    # Legacy code below unreachable

    
    if not cam.is_streaming:
        print("FAIL: Camera failed to start.")
        return
    
    print("PASS: Camera started.")
    
    print("\n[2] Waiting for auto-exposure stabilization (2s)...")
    time.sleep(2)
    
    print("\n[3] Capturing Frame 1...")
    img1 = cam.capture_frame()
    if img1:
        print(f"PASS: Frame 1 captured. Size: {len(img1)} bytes")
        with open("test_frame_1.jpg", "wb") as f:
            f.write(img1)
        print("Saved to test_frame_1.jpg")
    else:
        print("FAIL: Frame 1 capture failed.")

    print("\n[4] Capturing Frame 2...")
    img2 = cam.capture_frame()
    if img2:
        print(f"PASS: Frame 2 captured. Size: {len(img2)} bytes")
        with open("test_frame_2.jpg", "wb") as f:
            f.write(img2)
        print("Saved to test_frame_2.jpg")
    else:
        print("FAIL: Frame 2 capture failed.")
        
    print("\n[5] Stopping Camera...")
    cam.stop()
    print("PASS: Camera stopped.")
    print("--------------------------------------------------")
    print("Test Complete.")

if __name__ == "__main__":
    test_camera()
