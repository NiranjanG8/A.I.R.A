import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import speech_recognition as sr

from app.core.config import VOSK_MODEL_PATH

q = queue.Queue()

# -------- VOSK --------
try:
    vosk_model = Model(VOSK_MODEL_PATH)
    vosk_rec = KaldiRecognizer(vosk_model, 16000)
    VOSK_AVAILABLE = True
except Exception as e:
    print("Vosk error:", e)
    VOSK_AVAILABLE = False


def callback(indata, frames, time, status):
    q.put(bytes(indata))


def listen_vosk():
    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=callback
    ):
        print("🎤 Listening (offline)...")

        while True:
            data = q.get()
            if vosk_rec.AcceptWaveform(data):
                result = json.loads(vosk_rec.Result())
                text = result.get("text", "")
                if text:
                    print("Heard:", text)
                    return text.lower()


# -------- GOOGLE --------
def listen_google():
    r = sr.Recognizer()

    with sr.Microphone() as source:
        print("🎤 Listening (online)...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)

    try:
        command = r.recognize_google(audio)
        print("Heard:", command)
        return command.lower()
    except Exception as e:
        print("Google error:", e)
        return None


# -------- MAIN --------
def listen(mode="auto"):
    if mode == "offline":
        return listen_vosk()

    elif mode == "online":
        return listen_google()

    elif mode == "auto":
        if VOSK_AVAILABLE:
            try:
                return listen_vosk()
            except:
                return listen_google()
        else:
            return listen_google()
