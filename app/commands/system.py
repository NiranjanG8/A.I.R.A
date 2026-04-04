import subprocess
from datetime import datetime

import psutil


def get_time():
    return datetime.now().strftime("It's %I:%M %p")


def get_cpu():
    return f"CPU usage is {psutil.cpu_percent()} percent"


def get_battery():
    battery = psutil.sensors_battery()
    if battery:
        return f"Battery is {battery.percent} percent"
    return "Battery not available"


def open_notepad():
    subprocess.Popen(["notepad"])
