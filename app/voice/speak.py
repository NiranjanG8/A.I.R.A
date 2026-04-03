from piper import PiperVoice
import sounddevice as sd
import numpy as np

# Load voice once
voice = PiperVoice.load("tts/piper/en_US-lessac-medium.onnx")

def speak(text: str):
    print("Aira:", text)

    try:
        audio = b"".join(voice.synthesize(text))

        audio_np = np.frombuffer(audio, dtype=np.int16)
        sd.play(audio_np, samplerate=22050)
        sd.wait()

    except Exception as e:
        print("TTS error:", e)
