import sys
import threading
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

SAMPLE_RATE = 16000
recognizer = sr.Recognizer()
listening_event = threading.Event()


class Signals(QObject):
    text_received = pyqtSignal(str)
    status_changed = pyqtSignal(str, str)  # text, color
    reset_button = pyqtSignal()


signals = Signals()


def record_and_transcribe():
    signals.status_changed.emit("Listening...", "green")

    while listening_event.is_set():
        try:
            audio_np = sd.rec(
                int(5 * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocking=False,
            )
            # Wait in small increments so we can respond to stop quickly
            for _ in range(50):
                if not listening_event.is_set():
                    sd.stop()
                    break
                sd.sleep(100)

            # Bail out without transcribing if stopped mid-recording
            if not listening_event.is_set():
                break

            sd.wait()  # ensure recording is fully complete before reading

            raw = audio_np.flatten().tobytes()  # flatten (n,1) → (n,) for mono
            audio_data = sr.AudioData(raw, SAMPLE_RATE, 2)

            signals.status_changed.emit("Transcribing...", "blue")
            try:
                text = recognizer.recognize_google(audio_data)
                if text:
                    signals.text_received.emit(text + " ")
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                signals.status_changed.emit(f"API error: {e}", "red")
                listening_event.clear()
                signals.reset_button.emit()
                break

            if listening_event.is_set():
                signals.status_changed.emit("Listening...", "green")

        except Exception as e:
            signals.status_changed.emit(f"Error: {e}", "red")
            listening_event.clear()
            signals.reset_button.emit()
            break

    signals.status_changed.emit("Stopped.", "gray")


class TranscriberWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speech Transcriber")
        self.resize(620, 420)
        self._build_ui()
        signals.text_received.connect(self.append_text)
        signals.status_changed.connect(self.update_status)
        signals.reset_button.connect(self.reset_button_state)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()

        self.toggle_btn = QPushButton("Start Transcribing")
        self.toggle_btn.setFixedHeight(38)
        self.toggle_btn.setStyleSheet(
            "QPushButton { background:#2ecc71; color:white; font-size:14px;"
            "font-weight:bold; border:none; border-radius:6px; padding:0 16px; }"
            "QPushButton:hover { background:#27ae60; }"
        )
        self.toggle_btn.clicked.connect(self.toggle_listening)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(38)
        self.clear_btn.setStyleSheet(
            "QPushButton { background:#95a5a6; color:white; font-size:13px;"
            "border:none; border-radius:6px; padding:0 12px; }"
            "QPushButton:hover { background:#7f8c8d; }"
        )
        self.clear_btn.clicked.connect(self.clear_text)

        self.status_label = QLabel("Stopped.")
        self.status_label.setStyleSheet("color: gray; font-size: 13px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        toolbar.addWidget(self.toggle_btn)
        toolbar.addSpacing(8)
        toolbar.addWidget(self.clear_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.status_label)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(False)
        self.text_box.setStyleSheet(
            "QTextEdit { background:#f9f9f9; font-size:14px; border:1px solid #ddd; border-radius:6px; padding:8px; }"
        )

        layout.addLayout(toolbar)
        layout.addSpacing(8)
        layout.addWidget(self.text_box)

    def toggle_listening(self):
        if not listening_event.is_set():
            listening_event.set()
            self.toggle_btn.setText("Stop Transcribing")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background:#e74c3c; color:white; font-size:14px;"
                "font-weight:bold; border:none; border-radius:6px; padding:0 16px; }"
                "QPushButton:hover { background:#c0392b; }"
            )
            threading.Thread(target=record_and_transcribe, daemon=True).start()
        else:
            listening_event.clear()
            sd.stop()
            self.toggle_btn.setText("Start Transcribing")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background:#2ecc71; color:white; font-size:14px;"
                "font-weight:bold; border:none; border-radius:6px; padding:0 16px; }"
                "QPushButton:hover { background:#27ae60; }"
            )

    def reset_button_state(self):
        self.toggle_btn.setText("Start Transcribing")
        self.toggle_btn.setStyleSheet(
            "QPushButton { background:#2ecc71; color:white; font-size:14px;"
            "font-weight:bold; border:none; border-radius:6px; padding:0 16px; }"
            "QPushButton:hover { background:#27ae60; }"
        )

    def clear_text(self):
        self.text_box.clear()

    def append_text(self, text):
        self.text_box.moveCursor(self.text_box.textCursor().MoveOperation.End)
        self.text_box.insertPlainText(text)

    def update_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px;")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TranscriberWindow()
    window.show()
    sys.exit(app.exec())
