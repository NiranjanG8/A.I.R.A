import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
VOSK_DIR = ROOT / "models" / "vosk"
PIPER_DIR = ROOT / "tts" / "piper"
PIPER_EXE_PATH = PIPER_DIR / "piper.exe"

VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_ZIP = VOSK_DIR / "vosk-model.zip"
VOSK_MODEL_DIR = VOSK_DIR / "vosk-model-small-en-us-0.15"

PIPER_MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "en/en_US/lessac/medium/en_US-lessac-medium.onnx"
)
PIPER_CONFIG_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
)
PIPER_MODEL_PATH = PIPER_DIR / "en_US-lessac-medium.onnx"
PIPER_CONFIG_PATH = PIPER_DIR / "en_US-lessac-medium.onnx.json"


def info(message: str):
    print(f"[installer] {message}")


def download_file(url: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        info(f"Already present: {path}")
        return
    info(f"Downloading {url}")
    urllib.request.urlretrieve(url, path)
    info(f"Saved {path}")


def extract_zip(zip_path: Path, extract_to: Path):
    info(f"Extracting {zip_path}")
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    zip_path.unlink(missing_ok=True)
    info("Extraction complete")


def setup_vosk():
    if VOSK_MODEL_DIR.exists():
        info("Vosk model already exists")
        return
    download_file(VOSK_URL, VOSK_ZIP)
    extract_zip(VOSK_ZIP, VOSK_DIR)


def setup_piper_voice():
    if PIPER_MODEL_PATH.exists() and PIPER_CONFIG_PATH.exists():
        info("Piper voice files already exist")
        return
    download_file(PIPER_MODEL_URL, PIPER_MODEL_PATH)
    download_file(PIPER_CONFIG_URL, PIPER_CONFIG_PATH)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env(path: Path, values: dict[str, str]):
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_env_file():
    if ENV_PATH.exists():
        return
    source = ENV_EXAMPLE_PATH if ENV_EXAMPLE_PATH.exists() else None
    if source:
        ENV_PATH.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        ENV_PATH.write_text("", encoding="utf-8")
    info("Created .env")


def detect_ollama_model() -> str:
    vm = psutil.virtual_memory()
    ram_gb = vm.total / (1024 ** 3)
    free_disk_gb = shutil.disk_usage(ROOT).free / (1024 ** 3)
    cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count() or 4

    info(
        "Detected hardware: "
        f"{ram_gb:.1f} GB RAM, {free_disk_gb:.1f} GB free disk, {cpu_count} physical CPU cores"
    )

    if ram_gb >= 24 and free_disk_gb >= 16 and cpu_count >= 8:
        return "mistral:latest"
    if ram_gb >= 12 and free_disk_gb >= 8 and cpu_count >= 4:
        return "qwen2.5:3b"
    if ram_gb >= 8 and free_disk_gb >= 5:
        return "llama3.2:latest"
    return "tinyllama:latest"


def is_command_available(name: str) -> bool:
    return shutil.which(name) is not None


def run_command(args: list[str], check: bool = True):
    info("Running: " + " ".join(args))
    subprocess.run(args, cwd=ROOT, check=check)


def ensure_ollama_installed():
    if is_command_available("ollama"):
        info("Ollama CLI already available")
        return

    if sys.platform.startswith("win") and is_command_available("winget"):
        info("Installing Ollama with winget")
        run_command(["winget", "install", "-e", "--id", "Ollama.Ollama"])
        return

    raise RuntimeError(
        "Ollama is not installed. Install it from https://ollama.com/download and rerun the installer."
    )


def pull_ollama_model(model_name: str):
    run_command(["ollama", "pull", model_name])


def install_python_dependencies(python_exe: str):
    run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([python_exe, "-m", "pip", "install", "-r", "requirements.txt"])


def update_env_for_install(model_name: str):
    ensure_env_file()
    values = read_env(ENV_PATH)
    values.setdefault("OPENAI_API_KEY", "")
    values["USE_OLLAMA"] = "true"
    values.setdefault("USE_OPENAI", "false")
    values.setdefault("ASSISTANT_NAME", "Aira")
    values.setdefault("LISTEN_MODE", "auto")
    values.setdefault("VOSK_MODEL_PATH", "models/vosk/vosk-model-small-en-us-0.15")
    values.setdefault("PIPER_MODEL", "tts/piper/en_US-lessac-medium.onnx")
    values.setdefault("PIPER_CONFIG", "tts/piper/en_US-lessac-medium.onnx.json")
    values.setdefault("PIPER_EXE", "tts/piper/piper.exe")
    values["OLLAMA_MODEL"] = model_name
    write_env(ENV_PATH, values)
    info(f"Updated .env with OLLAMA_MODEL={model_name}")


def report_optional_components():
    if PIPER_EXE_PATH.exists():
        info(f"Found optional Piper executable: {PIPER_EXE_PATH}")
    else:
        info(
            "Optional Piper executable not found at tts/piper/piper.exe. "
            "Aira will still work with cloud TTS, Windows voice fallback, and the Python piper-tts package."
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Install Aira dependencies, models, and Ollama setup.")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use for pip installs")
    parser.add_argument(
        "--skip-ollama",
        action="store_true",
        help="Skip Ollama installation and model pull",
    )
    parser.add_argument(
        "--ollama-model",
        default="auto",
        help="Choose an Ollama model manually, or use 'auto' to detect based on system hardware",
    )
    parser.add_argument(
        "--skip-model-downloads",
        action="store_true",
        help="Skip Vosk and Piper model downloads",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    install_python_dependencies(args.python)

    if not args.skip_model_downloads:
        setup_vosk()
        setup_piper_voice()

    report_optional_components()

    selected_model = args.ollama_model
    if selected_model == "auto":
        selected_model = detect_ollama_model()

    if not args.skip_ollama:
        ensure_ollama_installed()
        pull_ollama_model(selected_model)

    update_env_for_install(selected_model)
    info("Setup complete")


if __name__ == "__main__":
    main()
