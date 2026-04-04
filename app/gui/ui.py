import math
import random
import sys
import time
from datetime import datetime

import psutil
from PyQt5 import QtCore, QtGui, QtWidgets

from app.core.config import ASSISTANT_NAME
from app.core.llm import translate_text
from app.core.router import route
from app.voice.listen import (
    LANGUAGE_OPTIONS,
    describe_listen_language,
    describe_listen_mode,
    get_listen_language,
    get_listen_mode,
    listen,
    set_listen_language,
    set_listen_mode,
)
from app.voice.speak import (
    SPEECH_SPEED_OPTIONS,
    describe_speech_speed,
    respeak_last_text_in_current_language_async,
    set_speech_speed,
    speak,
    stop_speaking,
)


class ArcReactor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0
        self.pulse = 0.0
        self.activity_level = 0.35
        self.wave = [0.0 for _ in range(120)]
        self.particles = [
            {"angle": random.uniform(0, 360), "radius": random.randint(90, 130)}
            for _ in range(12)
        ]
        self.setMinimumSize(260, 260)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(20)

    def set_activity_level(self, level: float):
        self.activity_level = max(0.2, min(level, 1.5))

    def animate(self):
        self.angle += 1
        self.pulse += 0.2
        self.wave = [
            0.6 + self.activity_level * math.sin(self.pulse + index * 0.2)
            for index in range(len(self.wave))
        ]
        for particle in self.particles:
            particle["angle"] += 1.5
        self.activity_level = max(0.35, self.activity_level * 0.96)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        center = QtCore.QPoint(width // 2, height // 2)

        painter.fillRect(self.rect(), QtGui.QColor(10, 0, 25))
        for index in range(6):
            radius = 120 + index * 8
            painter.setPen(QtGui.QPen(QtGui.QColor(180, 0, 255, 25 - index * 3), 3))
            painter.drawEllipse(center, radius, radius)

        painter.setBrush(QtGui.QColor(200, 0, 255))
        painter.setPen(QtCore.Qt.NoPen)
        for particle in self.particles:
            angle_rad = math.radians(particle["angle"])
            x_pos = center.x() + particle["radius"] * math.cos(angle_rad)
            y_pos = center.y() + particle["radius"] * math.sin(angle_rad)
            painter.drawEllipse(QtCore.QPointF(x_pos, y_pos), 3, 3)

        painter.save()
        painter.translate(center)
        painter.rotate(self.angle)
        painter.setPen(QtGui.QPen(QtGui.QColor(200, 0, 255), 2))
        for _ in range(20):
            painter.drawLine(0, 90, 0, 115)
            painter.rotate(18)
        painter.restore()

        painter.save()
        painter.translate(center)
        path = QtGui.QPainterPath()
        points = []
        base_radius = 75
        for index, value in enumerate(self.wave):
            angle = (index / len(self.wave)) * 2 * math.pi
            radius = base_radius + value * 20
            x_pos = radius * math.cos(angle)
            y_pos = radius * math.sin(angle)
            points.append(QtCore.QPointF(x_pos, y_pos))

        if points:
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            path.closeSubpath()

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 0, 255, 180), 2))
        painter.setBrush(QtGui.QColor(180, 0, 255, 60))
        painter.drawPath(path)
        painter.restore()
        painter.setBrush(QtGui.QColor(200, 0, 255))
        painter.drawEllipse(center, 30, 30)


class ListenerThread(QtCore.QThread):
    heard_command = QtCore.pyqtSignal(str)
    status_changed = QtCore.pyqtSignal(str)
    response_ready = QtCore.pyqtSignal(str)
    activity_event = QtCore.pyqtSignal(str)
    exit_requested = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False
        self.requestInterruption()

    def run(self):
        speak(f"{ASSISTANT_NAME} online")
        self.activity_event.emit(f"{ASSISTANT_NAME} system: Online")

        while self._running and not self.isInterruptionRequested():
            try:
                self.status_changed.emit("Listening...")
                command = listen(mode=get_listen_mode())

                if not self._running or self.isInterruptionRequested():
                    break

                if not command:
                    self.status_changed.emit("Listening...")
                    continue

                self.heard_command.emit(command)
                self.activity_event.emit(f"User command detected: {command}")
                self.status_changed.emit("Processing...")
                started_at = time.perf_counter()
                response = route(command)
                route_elapsed = time.perf_counter() - started_at

                if response == "exit":
                    self._running = False
                    stop_speaking()
                    self.response_ready.emit("Goodbye!")
                    self.activity_event.emit(f"{ASSISTANT_NAME} system: Shutdown")
                    self.activity_event.emit(f"{ASSISTANT_NAME} timing: route {route_elapsed:.2f}s | total {route_elapsed:.2f}s")
                    self.exit_requested.emit()
                    break

                translate_started_at = time.perf_counter()
                translated_response = translate_text(response, get_listen_language()) or response
                translate_elapsed = time.perf_counter() - translate_started_at
                total_elapsed = time.perf_counter() - started_at
                self.response_ready.emit(response)
                self.activity_event.emit(f"{ASSISTANT_NAME}: {translated_response}")
                self.activity_event.emit(
                    f"{ASSISTANT_NAME} timing: route {route_elapsed:.2f}s | translate {translate_elapsed:.2f}s | total {total_elapsed:.2f}s"
                )
                speak(translated_response)
                self.status_changed.emit("Listening...")
            except Exception as exc:
                self.activity_event.emit(f"{ASSISTANT_NAME} error: {exc}")
                self.status_changed.emit("Listening...")


class CommandWorker(QtCore.QThread):
    response_ready = QtCore.pyqtSignal(str)
    activity_event = QtCore.pyqtSignal(str)
    exit_requested = QtCore.pyqtSignal()

    def __init__(self, command: str):
        super().__init__()
        self.command = command.strip()

    def run(self):
        if not self.command:
            return

        self.activity_event.emit(f"Typed command detected: {self.command}")
        started_at = time.perf_counter()
        response = route(self.command)
        route_elapsed = time.perf_counter() - started_at
        if response == "exit":
            stop_speaking()
            self.response_ready.emit("Goodbye!")
            self.activity_event.emit(f"{ASSISTANT_NAME} system: Shutdown")
            self.activity_event.emit(f"{ASSISTANT_NAME} timing: route {route_elapsed:.2f}s | total {route_elapsed:.2f}s")
            self.exit_requested.emit()
            return

        translate_started_at = time.perf_counter()
        translated_response = translate_text(response, get_listen_language()) or response
        translate_elapsed = time.perf_counter() - translate_started_at
        total_elapsed = time.perf_counter() - started_at
        self.response_ready.emit(response)
        self.activity_event.emit(f"{ASSISTANT_NAME}: {translated_response}")
        self.activity_event.emit(
            f"{ASSISTANT_NAME} timing: route {route_elapsed:.2f}s | translate {translate_elapsed:.2f}s | total {total_elapsed:.2f}s"
        )
        speak(translated_response)


class AiraWindow(QtWidgets.QWidget):
    translated_activity_ready = QtCore.pyqtSignal(list, int)

    def __init__(self):
        super().__init__()
        self.listener = None
        self.command_worker = None
        self.activity_entries = []
        self._activity_translation_job_id = 0
        self._build_ui()
        self._start_timers()
        self.translated_activity_ready.connect(self._apply_translated_activity)

    def _build_ui(self):
        self.setWindowTitle("AIRA SYSTEM")
        self.resize(1080, 760)
        main_color = "#c000ff"

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: #050510;
                color: {main_color};
                font-family: Consolas;
            }}
            QGroupBox {{
                border: 2px solid {main_color};
                border-radius: 15px;
                margin-top: 15px;
                padding: 10px;
                background-color: rgba(20, 0, 40, 120);
            }}
            QLabel {{
                font-size: 22px;
                padding: 10px;
            }}
            QComboBox {{
                background-color: #120020;
                border: 1px solid {main_color};
                padding: 8px;
                font-size: 15px;
                color: #ffffff;
            }}
            QTextEdit {{
                background-color: #090012;
                border: none;
                color: #ffffff;
                font-size: 16px;
            }}
            """
        )

        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)

        self.cpu_label = QtWidgets.QLabel("CPU: 0%")
        self.cpu_label.setAlignment(QtCore.Qt.AlignCenter)
        self.time_label = QtWidgets.QLabel("TIME: --:--")
        self.time_label.setAlignment(QtCore.Qt.AlignCenter)
        self.battery_label = QtWidgets.QLabel("BATTERY: --")
        self.battery_label.setAlignment(QtCore.Qt.AlignCenter)
        self.mode_label = QtWidgets.QLabel(f"STT: {describe_listen_mode()}")
        self.mode_label.setAlignment(QtCore.Qt.AlignCenter)
        self.language_label = QtWidgets.QLabel(f"LANG: {describe_listen_language()}")
        self.language_label.setAlignment(QtCore.Qt.AlignCenter)
        self.speed_label = QtWidgets.QLabel(f"VOICE: {describe_speech_speed()}")
        self.speed_label.setAlignment(QtCore.Qt.AlignCenter)

        system_box = QtWidgets.QGroupBox("SYSTEM")
        system_layout = QtWidgets.QVBoxLayout()
        system_layout.addWidget(self.cpu_label)
        system_layout.addWidget(self.time_label)
        system_layout.addWidget(self.battery_label)
        system_layout.addWidget(self.mode_label)
        system_layout.addWidget(self.language_label)
        system_layout.addWidget(self.speed_label)
        system_box.setLayout(system_layout)

        self.reactor = ArcReactor()

        self.status_label = QtWidgets.QLabel("Starting...")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("Auto", "auto")
        self.mode_combo.addItem("Offline (Vosk)", "offline")
        self.mode_combo.addItem("Online (Google)", "online")
        self.mode_combo.currentIndexChanged.connect(self._handle_mode_change)

        self.language_combo = QtWidgets.QComboBox()
        for label, code in LANGUAGE_OPTIONS.items():
            self.language_combo.addItem(label, code)
        self.language_combo.currentIndexChanged.connect(self._handle_language_change)

        self.speed_combo = QtWidgets.QComboBox()
        for label, value in SPEECH_SPEED_OPTIONS.items():
            self.speed_combo.addItem(label, value)
        self.speed_combo.currentIndexChanged.connect(self._handle_speed_change)

        self.exit_button = QtWidgets.QPushButton("Exit")
        self.exit_button.clicked.connect(self._force_exit)

        status_box = QtWidgets.QGroupBox("STATUS")
        status_layout = QtWidgets.QVBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.mode_combo)
        status_layout.addWidget(self.language_combo)
        status_layout.addWidget(self.speed_combo)
        status_layout.addWidget(self.exit_button)
        status_box.setLayout(status_layout)

        self.command_view = QtWidgets.QTextEdit()
        self.command_view.setReadOnly(True)

        command_box = QtWidgets.QGroupBox("COMMAND")
        command_layout = QtWidgets.QVBoxLayout()
        command_layout.addWidget(self.command_view)

        self.command_input = QtWidgets.QLineEdit()
        self.command_input.setPlaceholderText("Type a command here...")
        self.command_input.returnPressed.connect(self._submit_typed_command)
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self._submit_typed_command)
        input_row = QtWidgets.QHBoxLayout()
        input_row.addWidget(self.command_input)
        input_row.addWidget(self.send_button)
        command_layout.addLayout(input_row)
        command_box.setLayout(command_layout)

        self.output_view = QtWidgets.QTextEdit()
        self.output_view.setReadOnly(True)

        output_box = QtWidgets.QGroupBox("OUTPUT")
        output_layout = QtWidgets.QVBoxLayout()
        output_layout.addWidget(self.output_view)
        output_box.setLayout(output_layout)

        self.activity_view = QtWidgets.QTextEdit()
        self.activity_view.setReadOnly(True)

        activity_box = QtWidgets.QGroupBox("ACTIVITY")
        activity_layout = QtWidgets.QVBoxLayout()
        activity_layout.addWidget(self.activity_view)
        activity_box.setLayout(activity_layout)

        layout.addWidget(system_box, 0, 0)
        layout.addWidget(self.reactor, 0, 1)
        layout.addWidget(status_box, 0, 2)
        layout.addWidget(command_box, 1, 0, 1, 2)
        layout.addWidget(output_box, 1, 2)
        layout.addWidget(activity_box, 2, 0, 1, 3)

        self.setLayout(layout)
        self._install_shortcuts()
        self._position_window()

    def _position_window(self):
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _start_timers(self):
        self.system_timer = QtCore.QTimer(self)
        self.system_timer.timeout.connect(self.update_system_stats)
        self.system_timer.start(1000)
        self.update_system_stats()

    def _install_shortcuts(self):
        QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self._force_exit)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, activated=self._force_exit)

    def _handle_mode_change(self):
        set_listen_mode(self.mode_combo.currentData())
        self.mode_label.setText(f"STT: {describe_listen_mode()}")

    def _handle_language_change(self):
        set_listen_language(self.language_combo.currentData())
        stop_speaking()
        self.language_label.setText(f"LANG: {describe_listen_language()}")
        self.append_activity(f"{ASSISTANT_NAME} system: Voice language changed to {describe_listen_language()}")
        self._refresh_activity_translation_async()
        respeak_last_text_in_current_language_async()

    def _handle_speed_change(self):
        set_speech_speed(self.speed_combo.currentData())
        self.speed_label.setText(f"VOICE: {describe_speech_speed()}")
        self.append_activity(f"{ASSISTANT_NAME} system: Voice speed changed to {describe_speech_speed()}")

    def attach_listener(self, listener: ListenerThread):
        self.listener = listener
        listener.status_changed.connect(self.update_status)
        listener.heard_command.connect(self.update_command)
        listener.response_ready.connect(self.update_output)
        listener.activity_event.connect(self.append_activity)
        listener.exit_requested.connect(self._force_exit)

    def update_system_stats(self):
        self.cpu_label.setText(f"CPU: {psutil.cpu_percent()}%")
        self.time_label.setText(datetime.now().strftime("%I:%M:%S %p"))
        battery = psutil.sensors_battery()
        self.mode_label.setText(f"STT: {describe_listen_mode()}")
        self.language_label.setText(f"LANG: {describe_listen_language()}")
        self.speed_label.setText(f"VOICE: {describe_speech_speed()}")
        if battery:
            self.battery_label.setText(f"BATTERY: {battery.percent}%")
        else:
            self.battery_label.setText("BATTERY: N/A")

    def update_status(self, text: str):
        self.status_label.setText(text)
        activity_map = {
            "Starting...": 0.45,
            "Listening...": 0.55,
            "Processing...": 1.15,
        }
        self.reactor.set_activity_level(activity_map.get(text, 0.75))

    def update_command(self, text: str):
        self.command_view.setPlainText(text)
        self.reactor.set_activity_level(1.25)

    def _submit_typed_command(self):
        command = self.command_input.text().strip()
        if not command:
            return
        self.command_input.clear()
        self.command_view.setPlainText(command)
        self.status_label.setText("Processing...")
        self.command_worker = CommandWorker(command)
        self.command_worker.response_ready.connect(self.update_output)
        self.command_worker.activity_event.connect(self.append_activity)
        self.command_worker.exit_requested.connect(self._force_exit)
        self.command_worker.finished.connect(lambda: self.status_label.setText("Listening..."))
        self.command_worker.start()

    def update_output(self, text: str):
        self.output_view.setPlainText(text)
        self.reactor.set_activity_level(0.95)

    def _refresh_activity_translation_async(self):
        source_entries = list(self.activity_entries)
        language_code = get_listen_language()
        self._activity_translation_job_id += 1
        job_id = self._activity_translation_job_id

        if not source_entries:
            self.activity_view.clear()
            return

        if language_code == "en-IN":
            self.activity_view.setPlainText("\n".join(source_entries))
            return

        def worker():
            translated_entries = []
            for entry in source_entries:
                if "] " in entry:
                    prefix, body = entry.split("] ", 1)
                    translated_body = translate_text(body, language_code) or body
                    translated_entries.append(f"{prefix}] {translated_body}")
                else:
                    translated_entries.append(translate_text(entry, language_code) or entry)
            self.translated_activity_ready.emit(translated_entries, job_id)

        QtCore.QThreadPool.globalInstance().start(_Runnable(worker))

    def _apply_translated_activity(self, entries: list, job_id: int):
        if job_id != self._activity_translation_job_id:
            return
        self.activity_view.setPlainText("\n".join(entries))

    def append_activity(self, text: str):
        timestamp = datetime.now().strftime("%I:%M:%S %p")
        self.activity_entries.append(f"[{timestamp}] {text}")
        self._refresh_activity_translation_async()

    def _force_exit(self):
        if self.listener is not None:
            self.listener.stop()
        stop_speaking()
        QtWidgets.QApplication.quit()

    def closeEvent(self, event):
        if self.listener is not None:
            self.listener.stop()
            self.listener.wait(1000)
            if self.listener.isRunning():
                self.listener.terminate()
                self.listener.wait(1000)
        stop_speaking()
        super().closeEvent(event)


def launch_ui():
    app = QtWidgets.QApplication(sys.argv)
    window = AiraWindow()
    listener = ListenerThread()
    window.attach_listener(listener)
    window.show()
    window.raise_()
    window.activateWindow()
    listener.start()
    sys.exit(app.exec_())


class _Runnable(QtCore.QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        self.fn()
