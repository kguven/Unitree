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
