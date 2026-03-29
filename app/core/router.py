from app.commands import system

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
        return "Sorry, I don't understand yet."
