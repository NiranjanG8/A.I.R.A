import os
import sys
from dotenv import load_dotenv

load_dotenv()


def resolve_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.getcwd())
    return os.path.join(base_path, relative_path)

ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "aira")

# STT mode: auto / offline / online
LISTEN_MODE = os.getenv("LISTEN_MODE", "auto")


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# Paths
VOSK_MODEL_PATH = resolve_path(
    os.getenv("VOSK_MODEL_PATH", "models/vosk/vosk-model-small-en-us-0.15")
)

# Piper TTS model assets used by the Python package
PIPER_MODEL = resolve_path(os.getenv("PIPER_MODEL", "tts/piper/en_US-lessac-medium.onnx"))
PIPER_CONFIG = resolve_path(
    os.getenv("PIPER_CONFIG", "tts/piper/en_US-lessac-medium.onnx.json")
)

# Local LLM via Ollama
USE_OLLAMA = env_flag("USE_OLLAMA", default=True)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

# Online LLM via OpenAI
USE_OPENAI = env_flag("USE_OPENAI", default=False)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
OPENAI_URL = os.getenv("OPENAI_URL", "https://api.openai.com/v1/responses")
