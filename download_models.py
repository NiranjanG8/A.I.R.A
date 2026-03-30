import os
import urllib.request
import zipfile

def download_and_extract(url, zip_path, extract_to):
    # Create folders if they don't exist
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    os.makedirs(extract_to, exist_ok=True)

    print("Downloading model...")
    urllib.request.urlretrieve(url, zip_path)
    print("Download complete.")

    print("Extracting model...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete.")

    # Optional: delete zip after extraction
    os.remove(zip_path)
    print("ZIP file removed.")

# ✅ Correct Vosk model URL
url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"

zip_path = "models/vosk/vosk-model-small-en-us-0.15.zip"
extract_to = "models/vosk/"

download_and_extract(url, zip_path, extract_to)
