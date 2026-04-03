import os
import urllib.request
import zipfile


# ------------------ HELPERS ------------------

def download_file(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        print(f"Already exists: {path}")
        return

    print(f"Downloading: {url}")
    urllib.request.urlretrieve(url, path)
    print(f"Saved to: {path}")


def extract_zip(zip_path, extract_to):
    print(f"Extracting: {zip_path}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete.")

    os.remove(zip_path)
    print("ZIP removed.")


# ------------------ VOSK ------------------

def setup_vosk():
    url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    zip_path = "models/vosk-model.zip"
    extract_to = "models/"

    if os.path.exists("models/vosk-model-small-en-us-0.15"):
        print("Vosk model already exists.")
        return

    download_file(url, zip_path)
    extract_zip(zip_path, extract_to)


# ------------------ PIPER VOICE ------------------

def setup_piper_voice():
    base_path = "tts/piper/"
    model_path = base_path + "en_US-lessac-medium.onnx"
    config_path = base_path + "en_US-lessac-medium.onnx.json"

    if os.path.exists(model_path):
        print("Piper voice model already exists.")
        return

    # Direct download links
    model_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
    config_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

    download_file(model_url, model_path)
    download_file(config_url, config_path)


# ------------------ MAIN ------------------

if __name__ == "__main__":
    print("🚀 Setting up AIRA models...\n")

    setup_vosk()
    setup_piper()
    setup_piper_voice()

    print("\n✅ All models ready!")
