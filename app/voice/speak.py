from piper import PiperVoice
import sounddevice as sd
import numpy as np
from app.core.config import PIPER_MODEL

# Load voice once
voice = PiperVoice.load(PIPER_MODEL)

def speak(text: str):
    print("Aira:", text)

    try:
        chunks = list(voice.synthesize(text))
        if not chunks:
            return

        audio = b"".join(chunk.audio_int16_bytes for chunk in chunks)
        sample_rate = chunks[0].sample_rate
        audio_np = np.frombuffer(audio, dtype=np.int16)
        sd.play(audio_np, samplerate=sample_rate)
        sd.wait()

    except Exception as e:
        print("TTS error:", e)
