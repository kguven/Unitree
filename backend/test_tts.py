import asyncio
import edge_tts

VOICE = "en-US-AriaNeural"

async def test_tts():
    print(f"edge-tts version: {edge_tts.__version__}")
    voice = "en-US-GuyNeural" 
    print(f"Testing TTS with voice: {voice}")
    communicate = edge_tts.Communicate("Hello world", voice)
    try:
        await communicate.save("test_audio.mp3")
        print("Success! Audio saved to test_audio.mp3")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
