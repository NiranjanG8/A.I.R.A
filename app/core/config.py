import os
from dotenv import load_dotenv

load_dotenv()

ASSISTANT_NAME = "aira"

# STT mode: auto / offline / online
LISTEN_MODE = "auto"

# Paths
VOSK_MODEL_PATH = "models/vosk-model-small-en-us-0.15"

# Piper TTS
PIPER_MODEL = "tts/piper/en_US-lessac-medium.onnx"
