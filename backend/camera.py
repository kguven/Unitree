"""
Camera capture module for Unitree G1 robot
Handles Network Camera interface (VideoHub) and image processing for AI analysis
Adapted from user example to support Remote PC (DDS/RPC) connection.
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
from config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, FPS

# --- Unitree SDK Import Logic ---
possible_sdk_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../unitree_sdk2_python")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../unitree_sdk2_python")),
]
for p in possible_sdk_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)

try:
    from unitree_sdk2py.rpc.client import Client
    SDK_AVAILABLE = True
except ImportError:
    print("unitree_sdk2py not found.")
    SDK_AVAILABLE = False


class G1VideoClient(Client):
    """
    Custom RPC Client for G1 Camera.
    """
    def __init__(self, service_name="videohub"):
        super().__init__(service_name, False)
        self.service_name = service_name

    def Init(self):
        self._SetApiVerson("1.0.0.1") 
        self._RegistApi(1001, 0)

    def GetImageSample(self):
        return self._CallBinary(1001, [])


class CameraCapture:
    """
    Camera capture class for Unitree G1 robot
    Provides methods to capture frames and prepare them for AI analysis
    """
    
    def __init__(self, camera_index: int = CAMERA_INDEX):
        """
        Initialize camera capture
        
        Args:
            camera_index: Index of camera (Not used for network, kept for compatibility)
        """
        self.camera_index = camera_index
        self.client = None # Replaces self.cap
        self.current_service = None
        self.is_initialized = False
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
    def initialize(self) -> bool:
        """
        Initialize network camera connection
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not SDK_AVAILABLE:
            self.logger.error("SDK not available. Cannot connect to robot camera.")
            return False

        service_candidates = ["videohub", "front_videohub", "depth_videohub"]
        
        for svc in service_candidates:
            self.logger.info(f"Trying to connect to video service: {svc}")
            try:
                c = G1VideoClient(svc)
                c.Init()
                # Light check?
                code, ver = c.GetServerApiVersion()
                if code == 0:
                    self.logger.info(f"Connected to {svc}. API Ver: {ver}")
                    self.client = c
                    self.current_service = svc
                    self.is_initialized = True
                    return True
            except Exception as e:
                self.logger.warning(f"Failed {svc}: {e}")
        
        self.logger.error("Failed to connect to any video service.")
        return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from camera (via Network)
        
        Returns:
            numpy.ndarray: Captured frame or None if failed
        """
        with self.lock:
            if not self.is_initialized or self.client is None:
                self.logger.error("Camera not initialized")
                # Try lazy init?
                if self.initialize():
                     pass # Retry below
                else:
                     return None
                
            try:
                # RPC Call
                code, data = self.client.GetImageSample()
                
                if code != 0 or not data:
                    self.logger.warning(f"Failed to capture frame (Code {code})")
                    return None
                
                # Data is bytes (JPEG usually). Decode to OpenCV
                image_bytes = bytes(data)
                np_arr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                return frame
                
            except Exception as e:
                self.logger.error(f"Frame capture failed: {e}")
                return None
    
    def frame_to_base64(self, frame: np.ndarray, format: str = 'JPEG') -> Optional[str]:
        """
        Convert OpenCV frame to base64 string for API transmission
        """
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            
            # Convert to bytes
            buffer = io.BytesIO()
            pil_image.save(buffer, format=format, quality=85)
            buffer.seek(0)
            
            # Encode to base64
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return img_base64
            
        except Exception as e:
            self.logger.error(f"Base64 conversion failed: {e}")
            return None
    
    def frame_to_pil(self, frame: np.ndarray) -> Optional[Image.Image]:
        """
        Convert OpenCV frame to PIL Image for Gemini API
        """
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            
            return pil_image
            
        except Exception as e:
            self.logger.error(f"PIL conversion failed: {e}")
            return None
    
    def get_frame_info(self) -> dict:
        """
        Get current camera frame information
        """
        if not self.is_initialized:
            return {}
        # Network camera info is static/unknown without query
        return {
            "service": self.current_service,
            "width": FRAME_WIDTH,
            "height": FRAME_HEIGHT,
            "fps": FPS
        }
    
    def release(self):
        """
        Release camera resources
        """
        # Nothing to release for UDP/RPC client really, just dereference
        self.client = None
        self.is_initialized = False
        self.logger.info("Camera client released")

    # Compatibility aliases
    def start(self): 
        self.initialize()
    
    def stop(self):
        self.release()

    
    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False

# Utility functions for camera testing
def test_camera_capture():
    """
    Test camera capture functionality
    """
    logging.basicConfig(level=logging.INFO)
    
    # Init Channel Factory for RPC
    try:
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize
        if len(sys.argv) > 1:
            ChannelFactoryInitialize(0, sys.argv[1])
        else:
            ChannelFactoryInitialize(0)
    except:
        pass

    with CameraCapture() as camera:
        if not camera.is_initialized:
            print("Failed to initialize camera")
            return
            
        print("Camera info:", camera.get_frame_info())
        
        # Capture test frame
        start = time.time()
        frame = camera.capture_frame()
        print(f"Capture took: {time.time()-start:.3f}s")
        
        if frame is not None:
            print(f"Captured frame shape: {frame.shape}")
            
            # Test base64 conversion
            base64_str = camera.frame_to_base64(frame)
            if base64_str:
                print(f"Base64 conversion successful, length: {len(base64_str)}")
            
            # Test PIL conversion
            pil_img = camera.frame_to_pil(frame)
            if pil_img:
                print(f"PIL conversion successful, size: {pil_img.size}")
                
            # Save test image
            cv2.imwrite('test_capture.jpg', frame)
            print("Test image saved as test_capture.jpg")
        else:
            print("Failed to capture frame")

if __name__ == "__main__":
    test_camera_capture()
