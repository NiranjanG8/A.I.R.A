# Aira AI Assistant 🤖

A local voice assistant with GUI built using Python.

## Features
- Voice commands
- System monitoring (CPU, Time)
- Offline speech recognition (Vosk)
- Text-to-speech (Piper)
- Offline LLM fallback with Ollama
- Custom GUI (Arc Reactor style)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Add speech models:
- Place the Vosk model in `models/vosk/vosk-model-small-en-us-0.15/`
- Place the Piper voice model files in `tts/piper/`
- `piper.exe` is not required because the app uses the installed `piper-tts` Python package

3. Optional: enable Ollama for offline chat fallback
- Install and run Ollama locally
- Pull a model, for example `ollama pull llama3.2`
- Set `USE_OLLAMA=true` in `.env`
- Optionally set `OLLAMA_MODEL=llama3.2`

4. Optional: enable OpenAI for online fallback
- Set `USE_OPENAI=true` in `.env`
- Add your `OPENAI_API_KEY`
- Optionally set `OPENAI_MODEL` if you want a different model
- The app uses the OpenAI Responses API for online text generation

5. Run:

```bash
python app/main.py
```
