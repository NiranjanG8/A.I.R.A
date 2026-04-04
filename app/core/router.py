import re

from app.commands import system
from app.core.llm import ask_llm

_memory = {
    "name": None,
    "age": None,
}


def _remember_name(name: str):
    cleaned = name.strip(" .,!?:;\"'")
    if not cleaned:
        return None
    _memory["name"] = cleaned.title()
    return f"Got it. I'll call you {_memory['name']}."


def _remember_age(age: str):
    cleaned = age.strip()
    if not cleaned.isdigit():
        return None
    _memory["age"] = cleaned
    return f"Okay. I remembered that you are {cleaned} years old."


def _name_response():
    if _memory["name"]:
        return f"Your name is {_memory['name']}."
    return "You haven't told me your name yet."


def _age_response():
    if _memory["age"]:
        return f"Your age is {_memory['age']}."
    return "You haven't told me your age yet."


def _match(pattern: str, command: str):
    return re.fullmatch(pattern, command.strip())


def route(command: str):
    if not command:
        return "I didn't catch that."

    command = command.lower().strip()

    name_match = _match(r"my name is (.+)", command)
    if name_match:
        return _remember_name(name_match.group(1)) or "Please tell me your name again."

    age_match = _match(r"my age is (\d+)", command)
    if age_match:
        return _remember_age(age_match.group(1)) or "Please tell me your age again."

    i_am_name_match = _match(r"(?:i am|i'm|call me) ([a-zA-Z .'-]+)", command)
    if i_am_name_match and not any(ch.isdigit() for ch in i_am_name_match.group(1)):
        return _remember_name(i_am_name_match.group(1)) or "Please tell me your name again."

    i_am_age_match = _match(r"(?:i am|i'm) (\d+)", command)
    if i_am_age_match:
        return _remember_age(i_am_age_match.group(1)) or "Please tell me your age again."

    hindi_name_match = _match(r"mera naa?m (.+) hai", command)
    if hindi_name_match:
        return _remember_name(hindi_name_match.group(1)) or "Kripya apna naam phir se batayein."

    hindi_age_match = _match(r"meri (?:umr|umar) (\d+) hai", command)
    if hindi_age_match:
        return _remember_age(hindi_age_match.group(1)) or "Kripya apni umr phir se batayein."

    hindi_name_script_match = _match(r"मेरा नाम (.+) है", command)
    if hindi_name_script_match:
        return _remember_name(hindi_name_script_match.group(1)) or "कृपया अपना नाम फिर से बताइए।"

    hindi_age_script_match = _match(r"मेरी (?:उम्र|उमर) (\d+) है", command)
    if hindi_age_script_match:
        return _remember_age(hindi_age_script_match.group(1)) or "कृपया अपनी उम्र फिर से बताइए।"

    telugu_name_match = _match(r"naa peru (.+)", command)
    if telugu_name_match:
        return _remember_name(telugu_name_match.group(1)) or "Mee peru malli cheppandi."

    telugu_name_script_match = _match(r"నా పేరు (.+)", command)
    if telugu_name_script_match:
        return _remember_name(telugu_name_script_match.group(1)) or "మీ పేరు మళ్లీ చెప్పండి."

    kannada_name_match = _match(r"nanna hesaru (.+)", command)
    if kannada_name_match:
        return _remember_name(kannada_name_match.group(1)) or "Dayavittu nimma hesarannu matte heli."

    kannada_name_script_match = _match(r"ನನ್ನ ಹೆಸರು (.+)", command)
    if kannada_name_script_match:
        return _remember_name(kannada_name_script_match.group(1)) or "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಹೆಸರನ್ನು ಮತ್ತೆ ಹೇಳಿ."

    kannada_age_script_match = _match(r"ನನ್ನ ವಯಸ್ಸು (\d+)", command)
    if kannada_age_script_match:
        return _remember_age(kannada_age_script_match.group(1)) or "ದಯವಿಟ್ಟು ನಿಮ್ಮ ವಯಸ್ಸನ್ನು ಮತ್ತೆ ಹೇಳಿ."

    if command in {"what is my name", "what's my name", "who am i", "who i am"}:
        return _name_response()

    if command in {
        "hello",
        "hi",
        "hey",
        "how are you",
        "how are you doing",
        "mera haal kaisa hai",
        "aap kaise ho",
        "aap kaise hain",
        "नमस्ते",
        "आप कैसे हैं",
        "क्या हाल है",
        "ನಮಸ್ಕಾರ",
        "ಹಾಯ್",
        "ಹೆಲೋ",
        "ಚೆನ್ನಾಗಿದ್ದೀರಾ",
        "ಹೇಗಿದ್ದೀರಾ",
        "ನೀವು ಹೇಗಿದ್ದೀರಾ",
        "నమస్తే",
        "హలో",
        "బాగున్నారా",
        "మీరు ఎలా ఉన్నారు",
    }:
        return "I'm doing well and ready to help."

    if command in {"what is my age", "what's my age"}:
        return _age_response()

    if command in {"mera naam kya hai", "mera nam kya hai", "main kaun hoon", "mai kaun hoon"}:
        return _name_response()

    if command in {"meri umr kya hai", "meri umar kya hai"}:
        return _age_response()

    if command in {"मेरा नाम क्या है", "मैं कौन हूँ"}:
        return _name_response()

    if command in {"मेरी उम्र क्या है", "मेरी उमर क्या है"}:
        return _age_response()

    if command in {"naa peru emiti", "na peru emiti", "nenu evarini"}:
        return _name_response()

    if command in {"naa vayasu enta", "na vayasu enta"}:
        return _age_response()

    if command in {"నా పేరు ఏమిటి", "నేను ఎవరు"}:
        return _name_response()

    if command in {"నా వయసు ఎంత"}:
        return _age_response()

    if command in {"nanna hesaru yenu", "nanna hesaru enu", "naanu yaaru"}:
        return _name_response()

    if command in {"nanna vayassu eshtu"}:
        return _age_response()

    if command in {"ನನ್ನ ಹೆಸರು ಏನು", "ನಾನು ಯಾರು"}:
        return _name_response()

    if command in {"ನನ್ನ ವಯಸ್ಸು ಎಷ್ಟು"}:
        return _age_response()

    if (
        "samay kya hai" in command
        or "समय क्या है" in command
        or "टाइम क्या है" in command
        or "वक्त क्या है" in command
        or "time" in command
        or "ಸಮಯ ಎಷ್ಟು" in command
        or "ಸಮಯ ಏನು" in command
        or "time enti" in command
        or "సమయం ఎంత" in command
        or "టైమ్ ఎంత" in command
    ):
        return system.get_time()

    if "battery kitni hai" in command or "बैटरी कितनी है" in command or "battery" in command or "ಬ್ಯಾಟರಿ ಎಷ್ಟು" in command:
        return system.get_battery()

    if "cpu" in command:
        return system.get_cpu()

    if (
        "notepad kholo" in command
        or "नोटपैड खोलो" in command
        or "नोटपैड खोलना" in command
        or "notepad khol do" in command
        or "open notepad" in command
        or "ನೋಟ್ಪ್ಯಾಡ್ ತೆರೆ" in command
        or "ನೋಟ್‌ಪ್ಯಾಡ್ ತೆರೆ" in command
        or "notepad teri" in command
        or "నోట్‌ప్యాడ్ తెరువు" in command
        or "నోట్ప్యాడ్ తెరువు" in command
        or "open note pad" in command
    ):
        system.open_notepad()
        return "Opening Notepad."

    exit_phrases = {
        "exit",
        "quit",
        "close",
        "close app",
        "close aira",
        "aira close",
        "stop",
        "stop listening",
        "shutdown",
        "shut down",
        "goodbye",
        "band karo",
        "बंद करो",
        "bahar niklo",
        "fek diya",
        "నిష్క్రమించు",
        "ఆపు",
        "మూసివేయి",
        "ಮುಚ್ಚು",
        "ನಿಲ್ಲಿಸು",
        "ಬಿಟ್ಟುಬಿಡು",
        "aira ಮುಚ್ಚು",
        "ಅಯ್ಯರ ಮುಚ್ಚು",
    }
    if any(phrase in command for phrase in exit_phrases):
        return "exit"

    response = ask_llm(command)
    if response:
        return response
    return "Sorry, I don't understand yet."
