"""
Camera capture module for Unitree G1 robot
Implemented using unitree_sdk2py.go2.video.video_client.VideoClient
"""

import cv2
import numpy as np
import base64
import io
import time
import sys
import os
from PIL import Image
from typing import Optional
import logging
import threading

# Import VideoClient from SDK
try:
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.go2.video.video_client import VideoClient
    SDK_AVAILABLE = True
except ImportError:
    print("unitree_sdk2py not found. Please ensure the SDK is installed.")
    SDK_AVAILABLE = False

# Camera Configuration
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS = 30

class CameraCapture:
    """
    Camera capture class using VideoClient (Network)
    """
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.client = None
        self.is_initialized = False
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
    def initialize(self) -> bool:
        """
        Initialize VideoClient
        """
        if not SDK_AVAILABLE:
            self.logger.error("unitree_sdk2py library not available.")
            return False

        if self.is_initialized:
            return True

        try:
            # Initialize ChannelFactory if not already done
            # Note: ChannelFactoryInitialize singleton behavior requires care
            # We assume robot_controller or main app might have called it, 
            # but we can try to call it safely.
            try:
                ChannelFactoryInitialize(0)
            except Exception:
                # Likely already initialized
                pass

            self.client = VideoClient()
            self.client.SetTimeout(3.0)
            self.client.Init()
            
            self.logger.info("VideoClient initialized.")
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize VideoClient: {e}")
            self.is_initialized = False
            self.client = None
            return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from VideoClient
        """
        with self.lock:
            if not self.is_initialized or self.client is None:
                # Try lazy initialization
                self.logger.info("Camera not initialized, trying to initialize...")
                if not self.initialize():
                    return None
                
            try:
                code, data = self.client.GetImageSample()
                
                if code != 0:
                    self.logger.warning(f"VideoClient GetImageSample failed with code: {code}")
                    # Allow retries or ignore occasional drops
                    return None
                
                # Convert bytes to numpy array
                image_data = np.frombuffer(bytes(data), dtype=np.uint8)
                # Decode JPEG/Raw data
                frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                if frame is None:
                    self.logger.warning("Failed to decode image data.")
                    return None
                
                return frame
                
            except Exception as e:
                self.logger.error(f"Frame capture failed: {e}")
                return None
    
    def frame_to_base64(self, frame: np.ndarray, format: str = 'JPEG') -> Optional[str]:
        """
        Convert OpenCV frame to base64 string
        """
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            buffer = io.BytesIO()
            pil_image.save(buffer, format=format, quality=85)
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return img_base64
        except Exception as e:
            self.logger.error(f"Base64 conversion failed: {e}")
            return None
    
    def frame_to_pil(self, frame: np.ndarray) -> Optional[Image.Image]:
        """
        Convert OpenCV frame to PIL Image
        """
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            return pil_image
        except Exception as e:
            self.logger.error(f"PIL conversion failed: {e}")
            return None
    
    def get_frame_info(self) -> dict:
        return {
            "width": FRAME_WIDTH,
            "height": FRAME_HEIGHT,
            "fps": FPS,
            "backend": "unitree_videoclient"
        }
    
    def release(self):
        """
        Release resources
        """
        self.client = None
        self.is_initialized = False
        self.logger.info("VideoClient released.")

    def start(self): 
        self.initialize()
    
    def stop(self):
        self.release()

    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

# Self-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with CameraCapture() as cam:
        if cam.is_initialized:
            print("Capture loop started. Press Ctrl+C to stop.")
            try:
                for i in range(5): # Capture 5 frames as test
                    start_t = time.time()
                    f = cam.capture_frame()
                    if f is not None:
                        print(f"Captured frame {i}: {f.shape} (Time: {time.time()-start_t:.3f}s)")
                        if i == 0:
                            cv2.imwrite("vc_test.jpg", f)
                            print("Saved vc_test.jpg")
                    else:
                        print("Failed to capture frame")
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass

