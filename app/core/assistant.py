from app.voice.listen import listen
from app.voice.speak import speak
from app.core.router import route
from app.core.config import ASSISTANT_NAME, LISTEN_MODE

def run():
    speak(f"{ASSISTANT_NAME} online")

    while True:
        command = listen(mode=LISTEN_MODE)

        if not command:
            continue

        response = route(command)

        if response == "exit":
            speak("Goodbye!")
            break

        speak(response)
