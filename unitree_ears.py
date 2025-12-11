import socket
import struct
import os
import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()

MCAST_GRP = os.getenv("UNITREE_MULTICAST_IP", "239.168.123.161")
MCAST_PORT = int(os.getenv("UNITREE_MULTICAST_PORT", 5555))
ROBOT_IFACE_IP = "0.0.0.0" # Bind to all is usually safest for receiving multicast

class UnitreeAudioSource(sr.AudioSource):
    def __init__(self):
        self.SAMPLE_RATE = 16000
        self.SAMPLE_WIDTH = 2 # 16-bit = 2 bytes
        self.CHANNELS = 1     # Mono
        self.CHUNK = 1024
        self.stream = UnitreeAudioStream()

    def __enter__(self):
        self.stream.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stream.close()

class UnitreeAudioStream:
    def __init__(self):
        self.sock = None
        self.buffer = b""

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Windows multicast loopback sometimes fails without this, but on Linux (Robot) it works.
            # self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

            self.sock.bind((ROBOT_IFACE_IP, MCAST_PORT))
            
            # Join Multicast Group
            mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            print(f"[Unitree Ears] Listening on {MCAST_GRP}:{MCAST_PORT}")
        except Exception as e:
            print(f"[Unitree Ears] Error binding socket: {e}")
            self.sock = None

    def read(self, size):
        # size is bytes to read
        if not self.sock:
            return b"\x00" * size # Return silence on error

        while len(self.buffer) < size:
            try:
                data, _ = self.sock.recvfrom(4096) # Buffer size from C++ snippet was 2048, we use 4k safe
                self.buffer += data
            except Exception as e:
                print(f"[Unitree Ears] Read error: {e}")
                return b"\x00" * size

        chunk = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return chunk

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

class UnitreeASRSubscriber:
    """
    Subscribes to the Unitree ASR topic ('rt/audio_msg') to receive recognized text.
    """
    def __init__(self, topic="rt/audio_msg"):
        self.topic = topic
        self.subscriber = None
        self.last_text = None
        self.last_index = -1 # Track message index to avoid duplicates
        self.is_listening = False
        
        # Try to import SDK
        try:
            from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
            from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_
            self.ChannelSubscriber = ChannelSubscriber
            self.ChannelFactoryInitialize = ChannelFactoryInitialize
            self.String_ = String_
            self.sdk_available = True
        except ImportError:
            print("[UnitreeASR] SDK not found. ASR disabled.")
            self.sdk_available = False

    def _handler(self, msg):
        # deserialized msg is String_ type
        # In python SDK, msg might be the object directly
        try:
            # msg.data is usually bytes or string in IDL mapping
            import json
            raw_data = msg.data
            # The C++ example shows it returns a JSON string
            # print(f"[UnitreeASR] Received: {raw_data}") # Debug logging reduced
            
            try:
                data = json.loads(raw_data)
                
                # Check index to avoid duplicates
                idx = data.get("index", -1)
                if idx != -1 and idx == self.last_index:
                    return # Duplicate message
                
                self.last_index = idx

                # Check language (Filter for English)
                # User example: "en - US", logs show "<|en|>"
                lang = data.get("language", "")
                if "en" not in lang.lower():
                    print(f"[UnitreeASR] Ignoring non-English: {lang}")
                    return
                
                # Check is_final
                is_final = data.get("is_final", False)
                if not is_final:
                    # Ignore intermediate results
                    print(f"[UnitreeASR] Ignoring intermediate: {data.get('text', '')}")
                    return

                # Looking for "text" field
                text = data.get("text", "")
                if text:
                    print(f"[UnitreeASR] New Text ({lang}, Final): {text}")
                    self.last_text = text
            except json.JSONDecodeError:
                # Fallback if not JSON
                self.last_text = raw_data
                
        except Exception as e:
            print(f"[UnitreeASR] Error handling message: {e}")

    def start(self):
        if not self.sdk_available:
            return
            
        if self.subscriber:
            return

        # Ensure ChannelFactory is initialized
        # We need the interface from env or default to eth0
        import os
        ROBOT_IFACE = os.getenv("ROBOT_NETWORK_INTERFACE", "eth0")
        try:
            # Domain ID 0 is default
            self.ChannelFactoryInitialize(0, ROBOT_IFACE)
            print(f"[UnitreeASR] Initialized ChannelFactory on {ROBOT_IFACE}")
        except Exception as e:
            # It might already be initialized, which is fine usually, or throw error if repeated.
            # We catch generic exception just in case specific "AlreadyInit" isn't exposed clearly.
            print(f"[UnitreeASR] Info: ChannelFactory init (may be already initialized): {e}")

        print(f"[UnitreeASR] Subscribing to {self.topic}...")
        try:
            self.subscriber = self.ChannelSubscriber(self.topic, self.String_)
            self.subscriber.Init(self._handler, 10) 
            self.is_listening = True
        except Exception as e:
             print(f"[UnitreeASR] Error initializing subscriber: {e}")
             raise e

    def stop(self):
        # SDK might not have explicit stop for subscriber depending on version, 
        # but usually we just let it be or close channel if unsupported.
        self.is_listening = False
        self.subscriber = None

    def get_last_text(self):
        t = self.last_text
        self.last_text = None # Clear after reading
        return t

