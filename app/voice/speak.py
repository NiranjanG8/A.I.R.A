import os
import queue
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import winsound

import requests

from app.core.config import PIPER_EXE, PIPER_MODEL
from app.core.llm import translate_text
from app.voice.listen import get_listen_language

try:
    from piper import PiperVoice
    import numpy as np
    import sounddevice as sd
    PIPER_IMPORT_ERROR = None
except Exception as exc:
    PiperVoice = None
    np = None
    sd = None
    PIPER_IMPORT_ERROR = exc


voice = None
VOICE_LOAD_ERROR = None
_ERROR_LOGGED = False
_PROCESS_LOCK = threading.Lock()
_CURRENT_PROCESS = None
_STATE_LOCK = threading.Lock()
_LAST_SOURCE_TEXT = ""
_SPEECH_EVENT_ID = 0
_SPEECH_QUEUE = queue.Queue()
_WORKER_STARTED = False
_CLOUD_TTS_URL = "https://translate.google.com/translate_tts"
_CLOUD_LANGUAGE_MAP = {
    "en-IN": "en",
    "hi-IN": "hi",
    "kn-IN": "kn",
    "te-IN": "te",
}
SPEECH_SPEED_OPTIONS = {
    "Slow": 0.85,
    "Normal": 1.0,
    "Fast": 1.2,
    "Very Fast": 1.4,
}
_CURRENT_SPEECH_SPEED = SPEECH_SPEED_OPTIONS["Normal"]


def _safe_console_text(text: str) -> str:
    try:
        encoding = sys.stdout.encoding or "utf-8"
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    except Exception:
        return text.encode("ascii", errors="replace").decode("ascii", errors="replace")


def get_speech_speed():
    return _CURRENT_SPEECH_SPEED


def set_speech_speed(speed_value: float):
    global _CURRENT_SPEECH_SPEED
    try:
        speed = float(speed_value)
    except Exception:
        speed = 1.0
    _CURRENT_SPEECH_SPEED = max(0.6, min(speed, 1.8))


def describe_speech_speed():
    current = get_speech_speed()
    closest_label = "Normal"
    closest_delta = float("inf")
    for label, value in SPEECH_SPEED_OPTIONS.items():
        delta = abs(current - value)
        if delta < closest_delta:
            closest_delta = delta
            closest_label = label
    return closest_label


def _set_current_process(process):
    global _CURRENT_PROCESS
    with _PROCESS_LOCK:
        _CURRENT_PROCESS = process


def _clear_current_process(process):
    global _CURRENT_PROCESS
    with _PROCESS_LOCK:
        if process is None or _CURRENT_PROCESS is process:
            _CURRENT_PROCESS = None


def _next_speech_event(remember_text=None):
    global _SPEECH_EVENT_ID, _LAST_SOURCE_TEXT
    with _STATE_LOCK:
        _SPEECH_EVENT_ID += 1
        if remember_text is not None:
            _LAST_SOURCE_TEXT = remember_text
        return _SPEECH_EVENT_ID


def _current_speech_event():
    with _STATE_LOCK:
        return _SPEECH_EVENT_ID


def _is_stale(event_id: int):
    return _current_speech_event() != event_id


def _last_source_text():
    with _STATE_LOCK:
        return _LAST_SOURCE_TEXT


def _drain_queue():
    while True:
        try:
            _SPEECH_QUEUE.get_nowait()
        except queue.Empty:
            break


def stop_speaking():
    global _CURRENT_PROCESS
    _next_speech_event()
    _drain_queue()

    try:
        if sd is not None:
            sd.stop()
    except Exception:
        pass

    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass

    with _PROCESS_LOCK:
        process = _CURRENT_PROCESS
        _CURRENT_PROCESS = None

    if process is None:
        return

    try:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=1)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _load_voice():
    global voice, VOICE_LOAD_ERROR, _ERROR_LOGGED

    if voice is not None or VOICE_LOAD_ERROR is not None:
        return voice

    if PIPER_IMPORT_ERROR is not None:
        VOICE_LOAD_ERROR = PIPER_IMPORT_ERROR
        if not _ERROR_LOGGED:
            print(f"TTS unavailable: {VOICE_LOAD_ERROR}")
            _ERROR_LOGGED = True
        return None

    try:
        voice = PiperVoice.load(PIPER_MODEL)
    except Exception as exc:
        VOICE_LOAD_ERROR = exc
        if not _ERROR_LOGGED:
            print(f"TTS unavailable: {VOICE_LOAD_ERROR}")
            _ERROR_LOGGED = True
        return None

    return voice


def _speak_with_piper_exe(text: str, event_id: int | None = None) -> bool:
    print(f"TTS fallback: checking exe at {PIPER_EXE}")
    if not os.path.exists(PIPER_EXE):
        print("TTS fallback: piper.exe not found")
        return False

    if not os.path.exists(PIPER_MODEL):
        print(f"TTS fallback model missing: {PIPER_MODEL}")
        return False

    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_wav.close()

    try:
        if event_id is not None and _is_stale(event_id):
            return False
        print(f"TTS fallback: synthesizing to {temp_wav.name}")
        process = subprocess.Popen(
            [PIPER_EXE, "--model", PIPER_MODEL, "--output_file", temp_wav.name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _set_current_process(process)
        stdout, stderr = process.communicate(input=text.encode("utf-8"), timeout=20)
        _clear_current_process(process)
        if event_id is not None and _is_stale(event_id):
            return False
        if process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="ignore").strip()
            stdout_text = stdout.decode("utf-8", errors="ignore").strip()
            if stdout_text:
                print(f"TTS fallback stdout: {stdout_text}")
            if stderr_text:
                print(f"TTS fallback error: {stderr_text}")
            return False

        if not os.path.exists(temp_wav.name):
            print("TTS fallback: wav file was not created")
            return False

        wav_size = os.path.getsize(temp_wav.name)
        print(f"TTS fallback: wav created ({wav_size} bytes)")
        if wav_size == 0:
            print("TTS fallback: wav file is empty")
            return False

        print("TTS fallback: attempting winsound playback")
        winsound.PlaySound(temp_wav.name, winsound.SND_FILENAME)
        print("TTS fallback: playback completed")
        return True
    except Exception as exc:
        print(f"TTS fallback exception: {exc}")
        return False
    finally:
        _clear_current_process(None)
        try:
            os.remove(temp_wav.name)
        except OSError:
            pass


def _speak_with_windows_voice(text: str, event_id: int | None = None) -> bool:
    language_code = get_listen_language()
    speed = get_speech_speed()
    sapi_rate = max(-10, min(10, round((speed - 1.0) * 20)))
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$voice = $speaker.GetInstalledVoices() | "
        "ForEach-Object { $_.VoiceInfo } | "
        f"Where-Object {{ $_.Gender -eq 'Female' -and $_.Culture.Name -eq '{language_code}' }} | "
        "Select-Object -First 1; "
        "if (-not $voice) { "
        "$voice = $speaker.GetInstalledVoices() | "
        "ForEach-Object { $_.VoiceInfo } | "
        "Where-Object { $_.Gender -eq 'Female' -and ($_.Culture.Name -in @('en-IN','hi-IN','kn-IN','te-IN')) } | "
        "Select-Object -First 1 }; "
        "if ($voice) { $speaker.SelectVoice($voice.Name) } "
        "else { $speaker.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female) }; "
        f"$speaker.Rate = {sapi_rate}; "
        "$speaker.Speak([Console]::In.ReadToEnd())"
    )

    try:
        if event_id is not None and _is_stale(event_id):
            return False
        print(f"TTS fallback: attempting Windows built-in voice ({language_code})")
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _set_current_process(process)
        _, stderr = process.communicate(input=text.encode("utf-8"), timeout=20)
        _clear_current_process(process)
        if event_id is not None and _is_stale(event_id):
            return False
        if process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="ignore").strip()
            if stderr_text:
                print(f"Windows voice error: {stderr_text}")
            return False

        print("TTS fallback: Windows voice completed")
        return True
    except Exception as exc:
        print(f"Windows voice exception: {exc}")
        return False


def _play_media_file(path: str, event_id: int | None = None) -> bool:
    speed = get_speech_speed()
    command = (
        "Add-Type -AssemblyName presentationCore; "
        "$player = New-Object System.Windows.Media.MediaPlayer; "
        f"$player.Open([Uri]'{path}'); "
        "$player.Volume = 1.0; "
        f"$player.SpeedRatio = {speed}; "
        "$player.Play(); "
        "while ($player.NaturalDuration.HasTimeSpan -eq $false) { Start-Sleep -Milliseconds 100 }; "
        f"$duration = [Math]::Ceiling($player.NaturalDuration.TimeSpan.TotalMilliseconds / {speed}); "
        "Start-Sleep -Milliseconds $duration; "
        "$player.Stop(); "
        "$player.Close()"
    )

    try:
        if event_id is not None and _is_stale(event_id):
            return False
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _set_current_process(process)
        _, stderr = process.communicate(timeout=30)
        _clear_current_process(process)
        if event_id is not None and _is_stale(event_id):
            return False
        if process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="ignore").strip()
            if stderr_text:
                print(f"Cloud audio playback error: {stderr_text}")
            return False
        return True
    except Exception as exc:
        print(f"Cloud audio playback exception: {exc}")
        return False


def _text_chunks(text: str, size: int = 180):
    words = text.split()
    current = []
    current_len = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_len + extra > size:
            yield " ".join(current)
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += extra
    if current:
        yield " ".join(current)


def _download_cloud_tts_chunk(text: str, language_code: str, output_path: str) -> bool:
    params = {
        "ie": "UTF-8",
        "client": "tw-ob",
        "tl": _CLOUD_LANGUAGE_MAP.get(language_code, "en"),
        "q": text,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://translate.google.com/",
    }

    try:
        response = requests.get(_CLOUD_TTS_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        with open(output_path, "wb") as file_handle:
            file_handle.write(response.content)
        return True
    except Exception as exc:
        print(f"Cloud TTS download error: {exc}")
        return False


def _speak_with_cloud_tts(text: str, event_id: int | None = None) -> bool:
    language_code = get_listen_language()
    if language_code not in _CLOUD_LANGUAGE_MAP:
        return False

    temp_paths = []
    try:
        for index, chunk in enumerate(_text_chunks(text), start=1):
            if event_id is not None and _is_stale(event_id):
                return False
            temp_file = tempfile.NamedTemporaryFile(suffix=f"_{index}.mp3", delete=False)
            temp_file.close()
            temp_paths.append(temp_file.name)
            if not _download_cloud_tts_chunk(chunk, language_code, temp_file.name):
                return False

        for path in temp_paths:
            if event_id is not None and _is_stale(event_id):
                return False
            if not _play_media_file(path, event_id=event_id):
                return False

        print(f"Cloud TTS: playback completed ({language_code})")
        return True
    finally:
        for path in temp_paths:
            try:
                os.remove(path)
            except OSError:
                pass


def _speak_sync(text: str, event_id: int):
    print("Aira:", _safe_console_text(text))

    if not _is_stale(event_id):
        if _speak_with_cloud_tts(text, event_id=event_id):
            return
        if _is_stale(event_id):
            return

    loaded_voice = _load_voice()
    if loaded_voice is None:
        if _is_stale(event_id):
            return
        if not _speak_with_piper_exe(text, event_id=event_id):
            if _is_stale(event_id):
                return
            _speak_with_windows_voice(text, event_id=event_id)
        return

    try:
        chunks = list(loaded_voice.synthesize(text))
        if not chunks or _is_stale(event_id):
            return

        audio = b"".join(chunk.audio_int16_bytes for chunk in chunks)
        sample_rate = max(8000, int(chunks[0].sample_rate * get_speech_speed()))
        audio_np = np.frombuffer(audio, dtype=np.int16)
        sd.play(audio_np, samplerate=sample_rate)
        sd.wait()
    except Exception as exc:
        print(f"TTS error: {exc}")
        if _is_stale(event_id):
            return
        if not _speak_with_piper_exe(text, event_id=event_id):
            if _is_stale(event_id):
                return
            _speak_with_windows_voice(text, event_id=event_id)


def _speech_worker():
    while True:
        item = _SPEECH_QUEUE.get()
        if item is None:
            continue

        text, remember_source, event_id = item
        if _is_stale(event_id):
            continue

        _speak_sync(text, event_id)


def _ensure_worker():
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return

    with _STATE_LOCK:
        if _WORKER_STARTED:
            return
        threading.Thread(target=_speech_worker, daemon=True).start()
        _WORKER_STARTED = True


def speak(text: str):
    event_id = _next_speech_event(remember_text=text)
    _ensure_worker()
    _SPEECH_QUEUE.put((text, text, event_id))


def respeak_last_text_in_current_language_async():
    source_text = _last_source_text()
    if not source_text:
        return

    def worker():
        translated = translate_text(source_text, get_listen_language()) or source_text
        event_id = _next_speech_event(remember_text=source_text)
        _ensure_worker()
        _SPEECH_QUEUE.put((translated, source_text, event_id))

    threading.Thread(target=worker, daemon=True).start()
