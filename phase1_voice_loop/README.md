# Habibot - Unitree Voice Interaction

This project provides a voice interaction loop for the Unitree robot (or any Python environment). It features:
*   **Wake Word Detection:** Uses `pvporcupine` (Porcupine) with the built-in keyword "porcupine".
*   **Speech-to-Text:** Uses `SpeechRecognition` (Google Web Speech API).
*   **Brain:** Uses Google Gemini API (`brain.py`) for character-based responses ("Habibot").
*   **Text-to-Speech:** Uses a robust **Offline Fallback** (`pyttsx3`) running in a separate process for valid audio output.

## Prerequisites (Jetson / Linux)

1.  **System Dependencies:**
    You may need to install audio libraries and `espeak` for the offline TTS engine.
    ```bash
    sudo apt-get update
    sudo apt-get install python3-pyaudio portaudio19-dev espeak libespeak1
    ```

2.  **Python Dependencies:**
    Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Environment Variables (.env):**
    Create a `.env` file in the root directory (see example below).
    You **MUST** correctly set the `GEMINI_API_KEY` and `PORCUPINE_ACCESS_KEY`.
    
    You also need to find the correct **Audio Device Indices** for your hardware (Microphone and Speaker).

    **To find device indices:**
    Run the helper script:
    ```bash
    python list_audio_devices.py
    ```
    Note the `Index` for your microphone and your speaker.

    **Example .env:**
    ```env
    # Keys
    GEMINI_API_KEY=your_gemini_api_key_here
    PORCUPINE_ACCESS_KEY=your_porcupine_access_key_here
    
    # Wake Word (Use 'porcupine' for built-in keyword)
    WAKE_WORD_PATH=porcupine
    
    # Audio Setup (CHANGE THESE to match 'list_audio_devices.py')
    MIC_DEVICE_INDEX=1
    SPEAKER_DEVICE_INDEX=4
    ```

## Usage

Run the main loop:

```bash
python main.py
```

### Interaction Flow:
1.  **Wait for "System ready":** The robot will speak "System ready" when initialized.
2.  **Wake Word:** Say **"Porcupine"** clearly.
    *   *Visual Feedback:* You will see dots `...` in the console while it listens.
    *   *Audio Feedback:* The robot will say "Yeah, I'm listening."
3.  **Command:** Ask your question (e.g., "What time is it?", "Tell me a joke").
4.  **Response:** The robot will process and speak the answer.

## Troubleshooting

*   **Silence / No Audio:**
    *   Check `SPEAKER_DEVICE_INDEX` in `.env`.
    *   Run `python test_offline_tts.py` to verify the speaker works independently.
    *   Ensure the volume is up.

*   **Wake Word not detected:**
    *   Check `MIC_DEVICE_INDEX` in `.env`.
    *   Run `python debug_audio_levels.py` to see if the microphone is picking up sound (look for `#` bars).

*   **"No audio received" errors:**
    *   The system is designed to fall back to `pyttsx3` (Offline) if the online TTS fails.
    *   If you see "Worker Error" in the logs, ensure `espeak` is installed (`sudo apt install espeak`).

## Architecture Notes
*   **`main.py`**: Orchestrates the loop.
*   **`mouth.py`**: Handles TTS. It uses `subprocess` to call `speak_worker.py`. This **Process Isolation** ensures that the audio engine never gets stuck or blocks the main loop.
*   **`speak_worker.py`**: A lightweight script that initializes the TTS engine, speaks one sentence, and exits.
