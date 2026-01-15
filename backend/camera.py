"""
Camera capture module for Unitree G1 robot
Simplified implementation using pyrealsense2 directly.
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

# Check for pyrealsense2
try:
    import pyrealsense2 as rs
    RS_AVAILABLE = True
except ImportError:
    print("pyrealsense2 not found. Please install it with: pip install pyrealsense2")
    RS_AVAILABLE = False

# Camera Configuration
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS = 30

class CameraCapture:
    """
    Camera capture class using pyrealsense2
    """
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.pipeline = None
        self.config = None
        self.is_initialized = False
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
    def initialize(self) -> bool:
        """
        Initialize RealSense pipeline
        """
        if not RS_AVAILABLE:
            self.logger.error("pyrealsense2 library not available.")
            return False

        if self.is_initialized:
            return True

        try:
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            
            self.logger.info(f"Configuring RealSense: {FRAME_WIDTH}x{FRAME_HEIGHT} @ {FPS}fps")
            
            # Enable Color Stream
            self.config.enable_stream(
                rs.stream.color, 
                FRAME_WIDTH, 
                FRAME_HEIGHT, 
                rs.format.bgr8, 
                FPS
            )
            
            # Start pipeline
            self.pipeline.start(self.config)
            
            # Warmup
            for _ in range(10):
                self.pipeline.wait_for_frames()
                
            self.is_initialized = True
            self.logger.info("RealSense camera initialized successfully.")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize RealSense: {e}")
            self.is_initialized = False
            self.pipeline = None
            return False
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from RealSense
        """
        with self.lock:
            if not self.is_initialized or self.pipeline is None:
                # Try lazy initialization
                self.logger.info("Camera not initialized, trying to initialize...")
                if not self.initialize():
                    return None
                
            try:
                # Wait for a coherent pair of frames: depth and color
                frames = self.pipeline.wait_for_frames(timeout_ms=5000)
                color_frame = frames.get_color_frame()
                
                if not color_frame:
                    self.logger.warning("No color frame received.")
                    return None
                
                # Convert images to numpy arrays
                frame = np.asanyarray(color_frame.get_data())
                
                return frame
                
            except RuntimeError as e:
                self.logger.error(f"RealSense runtime error: {e}")
                # Sometimes pipeline needs reset?
                return None
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
            "backend": "pyrealsense2"
        }
    
    def release(self):
        """
        Stop pipeline
        """
        if self.pipeline:
            try:
                self.pipeline.stop()
                self.logger.info("RealSense pipeline stopped.")
            except Exception as e:
                self.logger.warning(f"Error stopping pipeline: {e}")
        
        self.pipeline = None
        self.is_initialized = False

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
            f = cam.capture_frame()
            if f is not None:
                print(f"Captured frame: {f.shape}")
                cv2.imwrite("rs_test.jpg", f)
                print("Saved rs_test.jpg")
            else:
                print("Failed to capture frame")
