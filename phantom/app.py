import logging
import queue
import sys
import threading

import numpy as np

from phantom.clipboard import paste_text
from phantom.config import Config
from phantom.history import History
from phantom.hotkeys import HotkeyManager
from phantom.notes import append_note
from phantom.recorder import Recorder
from phantom.transcriber import Transcriber
from phantom.tray import TrayApp
from phantom.ui.history_window import HistoryWindow
from phantom.ui.settings_window import SettingsWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PhantomApp:
    def __init__(self):
        self._config = Config()
        self._history = History(self._config.data_dir)
        self._work_queue: queue.Queue[tuple[np.ndarray, str]] = queue.Queue()
        self._init_components()

    def _init_components(self):
        self._config = getattr(self, "_config", Config())
        self._history = getattr(self, "_history", History(self._config.data_dir))
        self._work_queue = getattr(self, "_work_queue", queue.Queue())

        self._recorder = Recorder(device=self._config.mic_device)
        self._hotkey_mgr = HotkeyManager()

        try:
            self._transcriber = Transcriber(model_size=self._config.model_size)
        except Exception:
            logger.exception("Failed to load Whisper model")
            self._transcriber = None

        self._tray = TrayApp(
            callbacks={
                "on_quit": self._shutdown,
                "on_history": self._show_history,
                "on_settings": self._show_settings,
            }
        )

        self._current_mode: str | None = None

    def _register_hotkeys(self):
        self._hotkey_mgr.register(
            self._config.hotkey_paste, lambda: self._toggle_recording("paste")
        )
        self._hotkey_mgr.register(
            self._config.hotkey_notes, lambda: self._toggle_recording("notes")
        )
        logger.info(
            "Hotkeys registered: paste=%s, notes=%s",
            self._config.hotkey_paste,
            self._config.hotkey_notes,
        )

    def _toggle_recording(self, mode: str):
        if self._transcriber is None:
            self._tray.notify("Whisper model not loaded")
            return

        if self._recorder.is_recording:
            # Stop recording
            logger.info("Stopping recording (mode=%s)", self._current_mode)
            audio = self._recorder.stop()
            self._tray.set_recording(False)
            if audio is not None:
                self._work_queue.put((audio, self._current_mode))
            else:
                logger.info("Recording too short, discarded")
            self._current_mode = None
        else:
            # Start recording
            self._current_mode = mode
            logger.info("Starting recording (mode=%s)", mode)
            self._recorder.start()
            self._tray.set_recording(True)

    def _transcription_worker(self):
        """Daemon thread: blocks on queue, transcribes audio, dispatches result."""
        while True:
            try:
                audio, mode = self._work_queue.get()
            except Exception:
                break

            try:
                logger.info("Transcribing audio (%d samples)...", len(audio))
                text = self._transcriber.transcribe(audio)

                if not text:
                    logger.info("Empty transcription, skipping")
                    continue

                logger.info("Transcribed: %s", text[:80])
                PhantomApp._process_audio_static(
                    audio=None,
                    mode=mode,
                    transcriber=None,
                    history=self._history,
                    tray=self._tray,
                    notes_path=self._config.data_dir / "notes.md",
                    text=text,
                )
            except Exception:
                logger.exception("Transcription failed")
                self._tray.notify("Transcription failed")

    @staticmethod
    def _process_audio_static(
        audio, mode, transcriber, history, tray, notes_path, text=None
    ):
        """Process transcribed audio. Static for testability."""
        if text is None:
            text = transcriber.transcribe(audio)

        if not text:
            return

        if mode == "paste":
            paste_text(text)
        elif mode == "notes":
            append_note(text, notes_path)

        history.add(text, mode)

    def _show_history(self):
        HistoryWindow(self._history).show()

    def _show_settings(self):
        SettingsWindow(self._config, on_save=self._on_settings_saved).show()

    def _on_settings_saved(self):
        """Reload components after settings change."""
        logger.info("Settings saved, reloading...")
        self._hotkey_mgr.unregister_all()
        self._register_hotkeys()
        self._recorder = Recorder(device=self._config.mic_device)
        # Note: model reload is expensive — only do it if model_size changed
        # For now, notify user to restart for model changes
        self._tray.notify("Settings saved. Restart for model changes.")

    def _shutdown(self):
        logger.info("Shutting down...")
        self._hotkey_mgr.unregister_all()
        self._tray.stop()

    def run(self):
        # Start transcription worker thread
        worker = threading.Thread(target=self._transcription_worker, daemon=True)
        worker.start()

        # Register hotkeys
        self._register_hotkeys()

        logger.info("PHANTOM is running. Press hotkeys to start recording.")

        # Run tray on main thread (blocks until quit)
        self._tray.run()


def main():
    app = PhantomApp()
    app.run()


if __name__ == "__main__":
    main()
