import subprocess
from app.core.config import PIPER_PATH, PIPER_MODEL

def speak(text: str):
    print("Aira:", text)

    try:
        subprocess.run(
            [
                PIPER_PATH,
                "--model", PIPER_MODEL,
                "--output-raw"
            ],
            input=text.encode("utf-8")
        )
    except Exception as e:
        print("TTS error:", e)
