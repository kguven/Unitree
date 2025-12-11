# Habibot - Unitree Voice Interaction

This project provides a voice interaction loop for the Unitree robot.

## Modes

1.  **Local Mode (Jetson/PC):**
    *   **Input:** USB Microphone (PyAudio).
    *   **Output:** Offline TTS (`pyttsx3`) or `edge_tts`.
    *   **Configuration:** `RUN_ON_ROBOT=False`.

2.  **Robot Mode (Unitree G1/Go2):**
    *   **Input:** **Multicast Audio Stream** (`239.168.123.161:5555`). This reads raw audio directly from the robot's network stream, similar to `vui_client` logic.
    *   **Output:** **Unitree SDK2** (`TtsMaker`). Uses the robot's onboard speaker engine.
    *   **Configuration:** `RUN_ON_ROBOT=True`.

## Prerequisites

### 1. System Dependencies (Linux/Jetson)
```bash
sudo apt-get update
sudo apt-get install python3-pyaudio portaudio19-dev espeak libespeak1
```

### 2. Python Dependencies
```bash
pip install -r requirements.txt
```
*Note: If using Robot Mode output, install the Unitree SDK (`pip install unitree-sdk2`).*

## Configuration (`.env`)

Create a `.env` file based on your environment:

### option A: Running on PC / Testing (Default)
```env
RUN_ON_ROBOT=False
MIC_DEVICE_INDEX=1       # Run 'python list_audio_devices.py' to find this
SPEAKER_DEVICE_INDEX=4   # Run 'python list_audio_devices.py' to find this
GEMINI_API_KEY=...
PORCUPINE_ACCESS_KEY=...
WAKE_WORD_PATH=porcupine
```

### option B: Running on Robot (Jetson Orin)
```env
RUN_ON_ROBOT=True
ROBOT_NETWORK_INTERFACE=eth0   # Interface connected to robot internal network
UNITREE_MULTICAST_IP=239.168.123.161
UNITREE_MULTICAST_PORT=5555

GEMINI_API_KEY=...
PORCUPINE_ACCESS_KEY=...
WAKE_WORD_PATH=porcupine
```

## Usage

Run the main loop:
```bash
python main.py
```

## How It Works
*   **`unitree_ears.py`**: A custom audio driver that joins the Robot's Multicast Group to receive 16kHz audio samples. This replaces standard microphone input when running on the robot.
*   **`mouth.py`**: Automatically switches between local `pyttsx3` (via `speak_worker.py` for stability) and the Unitree SDK `AudioClient`.
