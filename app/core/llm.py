import json
import urllib.error
import urllib.request

import requests

from app.core.config import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_URL,
    USE_OLLAMA,
    USE_OPENAI,
)

_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
_TRANSLATE_LANGUAGE_MAP = {
    "en-IN": "en",
    "hi-IN": "hi",
    "kn-IN": "kn",
    "te-IN": "te",
}
_FAST_ASSISTANT_PROMPT = (
    "You are Aira, a fast desktop voice assistant. "
    "Answer directly, practically, and briefly. "
    "Prefer 1 to 3 short sentences. "
    "Do not add long introductions, lists, or extra background unless the user clearly asks for depth."
)


def fetch_ollama_models():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [model.get("name") for model in data.get("models", []) if model.get("name")]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print("Ollama model list error:", error)
        return []


def resolve_ollama_model():
    available_models = fetch_ollama_models()
    if not available_models:
        return OLLAMA_MODEL

    if OLLAMA_MODEL in available_models:
        return OLLAMA_MODEL

    fallback_model = available_models[0]
    print(f"Ollama model '{OLLAMA_MODEL}' not found. Using '{fallback_model}' instead.")
    return fallback_model


def ask_ollama(prompt: str):
    if not USE_OLLAMA:
        return None

    model_name = resolve_ollama_model()

    payload = json.dumps(
        {
            "model": model_name,
            "prompt": f"{_FAST_ASSISTANT_PROMPT}\n\nUser request:\n{prompt}",
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 120,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            data = json.loads(response.read().decode("utf-8"))
            text = data.get("response", "").strip()
            return text or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print("Ollama error:", error)
        return None


def extract_openai_text(data):
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text = content.get("text", "").strip()
                if text:
                    return text

    return None


def ask_openai(prompt: str):
    if not USE_OPENAI or not OPENAI_API_KEY:
        return None

    payload = json.dumps(
        {
            "model": OPENAI_MODEL,
            "input": prompt,
            "instructions": "You are Aira, a concise helpful desktop voice assistant. Keep replies short and natural for speech.",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OPENAI_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return extract_openai_text(data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print("OpenAI error:", error)
        return None


def ask_llm(prompt: str):
    response = ask_ollama(prompt)
    if response:
        return response

    return ask_openai(prompt)


def translate_text_cloud(text: str, language_code: str):
    target = _TRANSLATE_LANGUAGE_MAP.get(language_code, "en")
    if target == "en":
        return text

    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": text,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    try:
        response = requests.get(_TRANSLATE_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        parts = data[0] if data and isinstance(data, list) else []
        translated = "".join(part[0] for part in parts if part and part[0])
        return translated.strip() or None
    except Exception as error:
        print("Cloud translate error:", error)
        return None


def translate_text(text: str, language_code: str):
    if not text:
        return None

    language_names = {
        "en-IN": "English",
        "hi-IN": "Hindi",
        "kn-IN": "Kannada",
        "te-IN": "Telugu",
    }
    script_names = {
        "en-IN": "Latin script",
        "hi-IN": "Devanagari script",
        "kn-IN": "Kannada script",
        "te-IN": "Telugu script",
    }
    target_language = language_names.get(language_code, "English")
    if target_language == "English":
        return text

    cloud_translation = translate_text_cloud(text, language_code)
    if cloud_translation:
        return cloud_translation

    target_script = script_names.get(language_code, "native script")
    prompt = (
        f"Translate the following assistant reply into fluent, natural {target_language} written in {target_script}. "
        f"Do not transliterate into English. Do not explain. Do not add labels. "
        f"Keep proper nouns only when necessary, but write the rest fully in {target_script}. "
        "Return only the final translated text.\n\n"
        f"Reply:\n{text}"
    )

    response = ask_ollama(prompt)
    if response:
        return response.strip()

    response = ask_openai(prompt)
    if response:
        return response.strip()

    return text
