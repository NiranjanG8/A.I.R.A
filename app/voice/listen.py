import json
import queue
import sys

import sounddevice as sd
import speech_recognition as sr
from vosk import KaldiRecognizer, Model

from app.core.config import LISTEN_MODE, VOSK_MODEL_PATH

q = queue.Queue()

LANGUAGE_OPTIONS = {
    "English (India)": "en-IN",
    "Hindi": "hi-IN",
    "Kannada": "kn-IN",
    "Telugu": "te-IN",
}

CURRENT_LISTEN_MODE = LISTEN_MODE
CURRENT_LISTEN_LANGUAGE = LANGUAGE_OPTIONS["English (India)"]


def _safe_console_text(text: str) -> str:
    try:
        encoding = sys.stdout.encoding or "utf-8"
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    except Exception:
        return text.encode("ascii", errors="replace").decode("ascii", errors="replace")


try:
    vosk_model = Model(VOSK_MODEL_PATH)
    vosk_rec = KaldiRecognizer(vosk_model, 16000)
    VOSK_AVAILABLE = True
except Exception as e:
    print("Vosk error:", e)
    VOSK_AVAILABLE = False
    vosk_rec = None


def callback(indata, frames, time, status):
    q.put(bytes(indata))


def get_listen_mode():
    return CURRENT_LISTEN_MODE


def set_listen_mode(mode: str):
    global CURRENT_LISTEN_MODE
    normalized = (mode or "auto").strip().lower()
    if normalized not in {"auto", "offline", "online"}:
        normalized = "auto"
    CURRENT_LISTEN_MODE = normalized


def get_listen_language():
    return CURRENT_LISTEN_LANGUAGE


def set_listen_language(language_code: str):
    global CURRENT_LISTEN_LANGUAGE
    if language_code in LANGUAGE_OPTIONS.values():
        CURRENT_LISTEN_LANGUAGE = language_code
    else:
        CURRENT_LISTEN_LANGUAGE = LANGUAGE_OPTIONS["English (India)"]


def describe_listen_mode():
    mode = get_listen_mode()
    if mode == "offline":
        return "Offline (Vosk)"
    if mode == "online":
        return "Online (Google)"
    return "Auto"


def describe_listen_language():
    current = get_listen_language()
    for label, code in LANGUAGE_OPTIONS.items():
        if code == current:
            return label
    return "English (India)"


def listen_vosk():
    if not VOSK_AVAILABLE or vosk_rec is None:
        return None

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        print("Listening (offline)...")
        while True:
            data = q.get()
            if vosk_rec.AcceptWaveform(data):
                result = json.loads(vosk_rec.Result())
                text = result.get("text", "")
                if text:
                    print("Heard:", _safe_console_text(text))
                    return text.lower()


def listen_google():
    recognizer = sr.Recognizer()
    language_code = get_listen_language()
    candidate_languages = [language_code]
    if "en-IN" not in candidate_languages:
        candidate_languages.append("en-IN")

    try:
        with sr.Microphone() as source:
            print(f"Listening (online, {language_code})...")
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)

        for candidate in candidate_languages:
            try:
                command = recognizer.recognize_google(audio, language=candidate)
                print(f"Heard ({candidate}):", _safe_console_text(command))
                return command.lower()
            except sr.UnknownValueError:
                continue

        print("Google could not understand audio in selected/fallback languages")
        return None
    except sr.WaitTimeoutError:
        print("Google listen timeout")
        return None
    except Exception as e:
        print("Google error:", e)
        return None


def listen(mode="auto"):
    active_mode = (mode or get_listen_mode()).strip().lower()
    language_code = get_listen_language()
    prefers_google = language_code != LANGUAGE_OPTIONS["English (India)"]

    if active_mode == "offline":
        if prefers_google:
            return listen_google()
        return listen_vosk()

    if active_mode == "online":
        return listen_google()

    if prefers_google:
        return listen_google()

    if VOSK_AVAILABLE:
        try:
            return listen_vosk()
        except Exception:
            return listen_google()

    return listen_google()
