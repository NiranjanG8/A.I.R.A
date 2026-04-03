from app.commands import system
from app.core.llm import ask_llm

def route(command: str):
    if not command:
        return "I didn't catch that."

    command = command.lower()

    if "time" in command:
        return system.get_time()

    elif "open notepad" in command:
        system.open_notepad()
        return "Opening Notepad"

    elif "exit" in command or "quit" in command:
        return "exit"

    else:
        response = ask_llm(command)
        if response:
            return response
        return "Sorry, I don't understand yet."
