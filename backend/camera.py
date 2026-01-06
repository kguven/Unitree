import pyrealsense2 as rs
import numpy as np
import time

class RealSenseCamera:
    def __init__(self, width=640, height=480, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.pipeline = None
        self.config = None
        self.is_streaming = False

    def start(self):
        if self.is_streaming:
            return

        print("[Camera] Initializing RealSense pipeline...")
        try:
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            
            # Enable RGB stream
            self.config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
            
            # Start streaming
            self.pipeline.start(self.config)
            self.is_streaming = True
            print("[Camera] Streaming started.")
            
            # Warmup
            time.sleep(1.0)
            
        except RuntimeError as e:
            print(f"[Camera] Connection failed: {e}")
            self.is_streaming = False
        except Exception as e:
            print(f"[Camera] Unexpected error: {e}")
            self.is_streaming = False

    def capture_frame(self):
        """
        Captures a single frame and returns JPEG bytes.
        Returns None if failed.
        """
        if not self.is_streaming or not self.pipeline:
            print("[Camera] Not streaming. Cannot capture.")
            return None

        try:
            # Wait for a coherent pair of frames: depth and color
            frames = self.pipeline.wait_for_frames(timeout_ms=5000)
            color_frame = frames.get_color_frame()
            
            if not color_frame:
                return None

            # Convert images to numpy arrays
            # The format is bgr8
            image = np.asanyarray(color_frame.get_data())
            
            # Compress to JPEG using opencv
            import cv2
            ret, buffer = cv2.imencode('.jpg', image)
            if ret:
                return buffer.tobytes()
            else:
                return None

        except Exception as e:
            print(f"[Camera] Capture failed: {e}")
            return None

    def stop(self):
        if self.is_streaming and self.pipeline:
            self.pipeline.stop()
            self.is_streaming = False
            print("[Camera] Streaming stopped.")
