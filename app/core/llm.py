import json
import urllib.error
import urllib.request

from app.core.config import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_URL,
    USE_OLLAMA,
    USE_OPENAI,
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
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
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
