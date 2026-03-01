# PHANTOM Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Windows system tray voice-to-text app with two modes: paste-to-focus and voice notes capture, using local Whisper transcription.

**Architecture:** Multi-threaded Python app. Main thread runs pystray event loop. Daemon threads handle global hotkeys (keyboard lib), audio recording (sounddevice), and transcription (faster-whisper). A queue.Queue connects recording output to the transcription worker. Results dispatch to clipboard paste (Mode 1) or markdown file append (Mode 2).

**Tech Stack:** Python 3.11+, faster-whisper, keyboard, sounddevice, pystray, pyperclip, pyautogui, Pillow, SQLite3 (stdlib), tkinter (stdlib)

---

## Task 0: Python Environment & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `phantom/__init__.py`

**Step 1: Verify Python version and create virtual environment**

The user has Python 3.13. faster-whisper requires ctranslate2 which may not support 3.13. Try installing first; if it fails, install Python 3.11 via pyenv-win or direct download.

Run:
```bash
python --version
python -m venv .venv
source .venv/Scripts/activate
```
Expected: Virtual environment created.

**Step 2: Create requirements.txt**

```
faster-whisper>=1.0.0
sounddevice>=0.4.6
keyboard>=0.13.5
pystray>=0.19.4
pyperclip>=1.8.2
pyautogui>=0.9.54
Pillow>=10.0.0
numpy>=1.24.0
```

**Step 3: Create pyproject.toml**

```toml
[project]
name = "phantom"
version = "0.1.0"
description = "Personal Voice-to-Text Engine for Windows"
requires-python = ">=3.11"

[project.scripts]
phantom = "phantom.app:main"
```

**Step 4: Create phantom/__init__.py**

```python
"""PHANTOM - Personal Voice-to-Text Engine for Windows."""
```

**Step 5: Install dependencies and verify**

Run:
```bash
pip install -r requirements.txt
```
Expected: All packages install successfully. If faster-whisper or ctranslate2 fails, investigate Python version compatibility and resolve before continuing.

**Step 6: Verify critical imports**

Run:
```bash
python -c "import faster_whisper; import sounddevice; import keyboard; import pystray; print('All imports OK')"
```
Expected: "All imports OK"

**Step 7: Install test dependencies**

Run:
```bash
pip install pytest
```

**Step 8: Commit**

```bash
git add requirements.txt pyproject.toml phantom/__init__.py
git commit -m "chore: project scaffolding with dependencies"
```

---

## Task 1: Config Module

**Files:**
- Create: `phantom/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing tests**

```python
# tests/test_config.py
import json
import os
import pytest
from phantom.config import Config


@pytest.fixture
def config_dir(tmp_path):
    """Use a temp directory instead of ~/phantom."""
    return tmp_path


def test_default_config_values(config_dir):
    cfg = Config(config_dir)
    assert cfg.model_size == "base"
    assert cfg.mic_device is None
    assert cfg.hotkey_paste == "ctrl+shift+v"
    assert cfg.hotkey_notes == "ctrl+shift+n"


def test_save_and_load_config(config_dir):
    cfg = Config(config_dir)
    cfg.model_size = "small"
    cfg.hotkey_paste = "ctrl+alt+v"
    cfg.save()

    cfg2 = Config(config_dir)
    assert cfg2.model_size == "small"
    assert cfg2.hotkey_paste == "ctrl+alt+v"
    # Unchanged values stay default
    assert cfg2.hotkey_notes == "ctrl+shift+n"


def test_creates_data_directory(tmp_path):
    data_dir = tmp_path / "phantom_data"
    cfg = Config(data_dir)
    assert data_dir.exists()


def test_handles_corrupted_config(config_dir):
    config_file = config_dir / "config.json"
    config_file.write_text("not valid json{{{")
    cfg = Config(config_dir)
    # Falls back to defaults
    assert cfg.model_size == "base"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.config'`

**Step 3: Write minimal implementation**

```python
# phantom/config.py
import json
from pathlib import Path

DEFAULTS = {
    "model_size": "base",
    "mic_device": None,
    "hotkey_paste": "ctrl+shift+v",
    "hotkey_notes": "ctrl+shift+n",
}


class Config:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path.home() / "phantom"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self.data_dir / "config.json"
        self._data: dict = {}
        self._load()

    def _load(self):
        if self._config_path.exists():
            try:
                self._data = json.loads(self._config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def save(self):
        payload = {
            "model_size": self.model_size,
            "mic_device": self.mic_device,
            "hotkey_paste": self.hotkey_paste,
            "hotkey_notes": self.hotkey_notes,
        }
        self._config_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    @property
    def model_size(self) -> str:
        return self._data.get("model_size", DEFAULTS["model_size"])

    @model_size.setter
    def model_size(self, value: str):
        self._data["model_size"] = value

    @property
    def mic_device(self) -> int | None:
        return self._data.get("mic_device", DEFAULTS["mic_device"])

    @mic_device.setter
    def mic_device(self, value: int | None):
        self._data["mic_device"] = value

    @property
    def hotkey_paste(self) -> str:
        return self._data.get("hotkey_paste", DEFAULTS["hotkey_paste"])

    @hotkey_paste.setter
    def hotkey_paste(self, value: str):
        self._data["hotkey_paste"] = value

    @property
    def hotkey_notes(self) -> str:
        return self._data.get("hotkey_notes", DEFAULTS["hotkey_notes"])

    @hotkey_notes.setter
    def hotkey_notes(self, value: str):
        self._data["hotkey_notes"] = value
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add phantom/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: add config module with JSON persistence"
```

---

## Task 2: History Module (SQLite)

**Files:**
- Create: `phantom/history.py`
- Create: `tests/test_history.py`

**Step 1: Write the failing tests**

```python
# tests/test_history.py
import pytest
from phantom.history import History


@pytest.fixture
def history(tmp_path):
    return History(tmp_path)


def test_add_and_get_entries(history):
    history.add("Hello world", "paste")
    history.add("Buy groceries", "notes")
    entries = history.get_all()
    assert len(entries) == 2
    assert entries[0]["text"] == "Buy groceries"  # Most recent first
    assert entries[0]["mode"] == "notes"
    assert entries[1]["text"] == "Hello world"
    assert entries[1]["mode"] == "paste"


def test_entries_have_timestamps(history):
    history.add("Test entry", "paste")
    entries = history.get_all()
    assert "timestamp" in entries[0]
    assert len(entries[0]["timestamp"]) > 0


def test_max_50_entries(history):
    for i in range(55):
        history.add(f"Entry {i}", "paste")
    entries = history.get_all()
    assert len(entries) == 50
    # Oldest 5 should be pruned
    assert entries[-1]["text"] == "Entry 5"


def test_get_entry_by_id(history):
    history.add("Find me", "paste")
    entries = history.get_all()
    entry = history.get_by_id(entries[0]["id"])
    assert entry["text"] == "Find me"


def test_empty_history(history):
    entries = history.get_all()
    assert entries == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.history'`

**Step 3: Write minimal implementation**

```python
# phantom/history.py
import sqlite3
from datetime import datetime
from pathlib import Path

MAX_ENTRIES = 50


class History:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path.home() / "phantom"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.data_dir / "history.db"
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def add(self, text: str, mode: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO history (text, mode, timestamp) VALUES (?, ?, ?)",
                (text, mode, now),
            )
            self._prune(conn)

    def _prune(self, conn: sqlite3.Connection):
        conn.execute(
            """DELETE FROM history WHERE id NOT IN (
                SELECT id FROM history ORDER BY id DESC LIMIT ?
            )""",
            (MAX_ENTRIES,),
        )

    def get_all(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, text, mode, timestamp FROM history ORDER BY id DESC"
            ).fetchall()
        return [
            {"id": r[0], "text": r[1], "mode": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def get_by_id(self, entry_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, text, mode, timestamp FROM history WHERE id = ?",
                (entry_id,),
            ).fetchone()
        if row is None:
            return None
        return {"id": row[0], "text": row[1], "mode": row[2], "timestamp": row[3]}
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_history.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add phantom/history.py tests/test_history.py
git commit -m "feat: add history module with SQLite storage and auto-pruning"
```

---

## Task 3: Notes Module (Markdown Append)

**Files:**
- Create: `phantom/notes.py`
- Create: `tests/test_notes.py`

**Step 1: Write the failing tests**

```python
# tests/test_notes.py
import pytest
from phantom.notes import append_note


@pytest.fixture
def notes_file(tmp_path):
    return tmp_path / "notes.md"


def test_append_creates_file_if_missing(notes_file):
    append_note("First note", notes_file)
    assert notes_file.exists()
    content = notes_file.read_text(encoding="utf-8")
    assert "First note" in content


def test_append_adds_timestamp_header(notes_file):
    append_note("Test note", notes_file)
    content = notes_file.read_text(encoding="utf-8")
    # Should have a ## YYYY-MM-DD HH:MM header
    assert content.startswith("## ")


def test_multiple_appends(notes_file):
    append_note("Note one", notes_file)
    append_note("Note two", notes_file)
    content = notes_file.read_text(encoding="utf-8")
    assert "Note one" in content
    assert "Note two" in content
    # Should have two headers
    assert content.count("## ") == 2


def test_notes_separated_by_blank_lines(notes_file):
    append_note("First", notes_file)
    append_note("Second", notes_file)
    content = notes_file.read_text(encoding="utf-8")
    # Each entry should be separated
    assert "\n\n" in content
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.notes'`

**Step 3: Write minimal implementation**

```python
# phantom/notes.py
import fcntl
import os
from datetime import datetime
from pathlib import Path


def _get_lock_fn():
    """Return platform-appropriate file locking function."""
    try:
        import msvcrt

        def _lock(f):
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

        def _unlock(f):
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

        return _lock, _unlock
    except ImportError:
        import fcntl

        def _lock(f):
            fcntl.flock(f, fcntl.LOCK_EX)

        def _unlock(f):
            fcntl.flock(f, fcntl.LOCK_UN)

        return _lock, _unlock


_lock_file, _unlock_file = _get_lock_fn()


def append_note(text: str, notes_path: Path | None = None):
    if notes_path is None:
        notes_path = Path.home() / "phantom" / "notes.md"

    notes_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"## {timestamp}\n{text}\n\n"

    with open(notes_path, "a", encoding="utf-8") as f:
        _lock_file(f)
        try:
            f.write(entry)
        finally:
            _unlock_file(f)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_notes.py -v`
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add phantom/notes.py tests/test_notes.py
git commit -m "feat: add notes module with timestamped markdown append"
```

---

## Task 4: Clipboard / Paste Module

**Files:**
- Create: `phantom/clipboard.py`
- Create: `tests/test_clipboard.py`

**Step 1: Write the failing tests**

```python
# tests/test_clipboard.py
from unittest.mock import patch, call
import pytest
from phantom.clipboard import paste_text


@patch("phantom.clipboard.pyautogui")
@patch("phantom.clipboard.pyperclip")
def test_paste_sets_clipboard_and_simulates_paste(mock_pyperclip, mock_pyautogui):
    paste_text("Hello world")
    mock_pyperclip.copy.assert_called_once_with("Hello world")
    mock_pyautogui.hotkey.assert_called_once_with("ctrl", "v")


@patch("phantom.clipboard.pyautogui")
@patch("phantom.clipboard.pyperclip")
def test_paste_empty_string_does_nothing(mock_pyperclip, mock_pyautogui):
    paste_text("")
    mock_pyperclip.copy.assert_not_called()
    mock_pyautogui.hotkey.assert_not_called()


@patch("phantom.clipboard.pyautogui")
@patch("phantom.clipboard.pyperclip")
def test_paste_strips_whitespace(mock_pyperclip, mock_pyautogui):
    paste_text("  Hello  ")
    mock_pyperclip.copy.assert_called_once_with("Hello")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_clipboard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.clipboard'`

**Step 3: Write minimal implementation**

```python
# phantom/clipboard.py
import time

import pyautogui
import pyperclip


def paste_text(text: str):
    text = text.strip()
    if not text:
        return

    pyperclip.copy(text)
    time.sleep(0.1)  # Brief delay for clipboard reliability
    pyautogui.hotkey("ctrl", "v")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_clipboard.py -v`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add phantom/clipboard.py tests/test_clipboard.py
git commit -m "feat: add clipboard module for paste-to-focus"
```

---

## Task 5: Recorder Module (Audio Capture)

**Files:**
- Create: `phantom/recorder.py`
- Create: `tests/test_recorder.py`

**Step 1: Write the failing tests**

```python
# tests/test_recorder.py
from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from phantom.recorder import Recorder


def test_recorder_initial_state():
    rec = Recorder()
    assert rec.is_recording is False


@patch("phantom.recorder.sd")
def test_start_recording(mock_sd):
    rec = Recorder()
    rec.start()
    assert rec.is_recording is True
    mock_sd.InputStream.assert_called_once()


@patch("phantom.recorder.sd")
def test_stop_recording_returns_audio(mock_sd):
    rec = Recorder()
    # Simulate some audio chunks being captured
    rec._chunks = [np.zeros((1600,), dtype=np.float32) for _ in range(10)]
    rec._recording = True
    rec._stream = MagicMock()
    audio = rec.stop()
    assert audio is not None
    assert isinstance(audio, np.ndarray)
    assert len(audio) == 16000  # 10 chunks * 1600 samples


@patch("phantom.recorder.sd")
def test_stop_short_recording_returns_none(mock_sd):
    rec = Recorder()
    # Only 0.3 seconds of audio (below 0.5s threshold)
    rec._chunks = [np.zeros((1600,), dtype=np.float32) for _ in range(3)]
    rec._recording = True
    rec._stream = MagicMock()
    audio = rec.stop()
    assert audio is None


@patch("phantom.recorder.sd")
def test_stop_when_not_recording_returns_none(mock_sd):
    rec = Recorder()
    audio = rec.stop()
    assert audio is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_recorder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.recorder'`

**Step 3: Write minimal implementation**

```python
# phantom/recorder.py
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
MIN_DURATION_SEC = 0.5


class Recorder:
    def __init__(self, device: int | None = None):
        self._device = device
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording:
            self._chunks.append(indata[:, 0].copy())

    def start(self):
        self._chunks = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=self._device,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray | None:
        if not self._recording:
            return None

        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._chunks:
            return None

        audio = np.concatenate(self._chunks)
        duration = len(audio) / SAMPLE_RATE

        if duration < MIN_DURATION_SEC:
            return None

        return audio
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_recorder.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add phantom/recorder.py tests/test_recorder.py
git commit -m "feat: add recorder module with sounddevice audio capture"
```

---

## Task 6: Transcriber Module

**Files:**
- Create: `phantom/transcriber.py`
- Create: `tests/test_transcriber.py`

**Step 1: Write the failing tests**

```python
# tests/test_transcriber.py
from unittest.mock import patch, MagicMock
import numpy as np
import pytest
from phantom.transcriber import Transcriber


@patch("phantom.transcriber.WhisperModel")
def test_transcriber_loads_model(mock_model_cls):
    t = Transcriber(model_size="tiny")
    mock_model_cls.assert_called_once()
    call_kwargs = mock_model_cls.call_args
    assert call_kwargs[0][0] == "tiny"


@patch("phantom.transcriber.WhisperModel")
def test_transcribe_returns_text(mock_model_cls):
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = " Hello world "
    mock_info = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    mock_model_cls.return_value = mock_model

    t = Transcriber(model_size="base")
    audio = np.zeros((16000,), dtype=np.float32)
    result = t.transcribe(audio)
    assert result == "Hello world"


@patch("phantom.transcriber.WhisperModel")
def test_transcribe_empty_segments_returns_empty(mock_model_cls):
    mock_model = MagicMock()
    mock_info = MagicMock()
    mock_model.transcribe.return_value = ([], mock_info)
    mock_model_cls.return_value = mock_model

    t = Transcriber(model_size="base")
    audio = np.zeros((16000,), dtype=np.float32)
    result = t.transcribe(audio)
    assert result == ""


@patch("phantom.transcriber.WhisperModel")
def test_transcribe_joins_multiple_segments(mock_model_cls):
    mock_model = MagicMock()
    seg1 = MagicMock()
    seg1.text = " Hello "
    seg2 = MagicMock()
    seg2.text = " world "
    mock_info = MagicMock()
    mock_model.transcribe.return_value = ([seg1, seg2], mock_info)
    mock_model_cls.return_value = mock_model

    t = Transcriber(model_size="base")
    audio = np.zeros((16000,), dtype=np.float32)
    result = t.transcribe(audio)
    assert result == "Hello world"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transcriber.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.transcriber'`

**Step 3: Write minimal implementation**

```python
# phantom/transcriber.py
import logging

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def _detect_device() -> tuple[str, str]:
    """Auto-detect CUDA GPU, fall back to CPU with int8."""
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


class Transcriber:
    def __init__(self, model_size: str = "base"):
        device, compute_type = _detect_device()
        logger.info(
            "Loading Whisper model '%s' on %s (%s)", model_size, device, compute_type
        )
        self._model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )

    def transcribe(self, audio: np.ndarray) -> str:
        segments, info = self._model.transcribe(audio, beam_size=5, vad_filter=True)
        # Segments is a generator; consume it
        texts = []
        for segment in segments:
            texts.append(segment.text.strip())
        return " ".join(texts).strip()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transcriber.py -v`
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add phantom/transcriber.py tests/test_transcriber.py
git commit -m "feat: add transcriber module with faster-whisper and GPU auto-detect"
```

---

## Task 7: Tray Module (System Tray Icon)

**Files:**
- Create: `phantom/tray.py`
- Create: `tests/test_tray.py`

**Step 1: Write the failing tests**

```python
# tests/test_tray.py
from unittest.mock import patch, MagicMock
import pytest
from phantom.tray import create_icon_image, TrayApp


def test_create_icon_image_idle():
    img = create_icon_image(recording=False)
    assert img.size == (64, 64)


def test_create_icon_image_recording():
    img = create_icon_image(recording=True)
    assert img.size == (64, 64)


def test_create_icon_images_differ():
    idle = create_icon_image(recording=False)
    rec = create_icon_image(recording=True)
    # They should be different images (different colors)
    assert idle.tobytes() != rec.tobytes()


@patch("phantom.tray.pystray")
def test_tray_app_creation(mock_pystray):
    callbacks = {"on_quit": MagicMock(), "on_history": MagicMock(), "on_settings": MagicMock()}
    tray = TrayApp(callbacks)
    assert tray is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tray.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.tray'`

**Step 3: Write minimal implementation**

```python
# phantom/tray.py
from PIL import Image, ImageDraw
import pystray


def create_icon_image(recording: bool = False) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if recording:
        # Red circle when recording
        draw.ellipse([8, 8, size - 8, size - 8], fill=(220, 50, 50, 255))
    else:
        # Grey circle when idle
        draw.ellipse([8, 8, size - 8, size - 8], fill=(160, 160, 160, 255))

    # Inner "P" shape suggestion — small white dot
    center = size // 2
    r = 6
    draw.ellipse(
        [center - r, center - r, center + r, center + r], fill=(255, 255, 255, 255)
    )
    return img


class TrayApp:
    def __init__(self, callbacks: dict):
        self._callbacks = callbacks
        self._icon = pystray.Icon(
            "phantom",
            icon=create_icon_image(recording=False),
            title="PHANTOM - Voice to Text",
            menu=pystray.Menu(
                pystray.MenuItem("History", self._on_history),
                pystray.MenuItem("Settings", self._on_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._on_quit),
            ),
        )

    def _on_history(self, icon, item):
        cb = self._callbacks.get("on_history")
        if cb:
            cb()

    def _on_settings(self, icon, item):
        cb = self._callbacks.get("on_settings")
        if cb:
            cb()

    def _on_quit(self, icon, item):
        icon.stop()
        cb = self._callbacks.get("on_quit")
        if cb:
            cb()

    def set_recording(self, recording: bool):
        self._icon.icon = create_icon_image(recording=recording)

    def notify(self, message: str):
        self._icon.notify(message, "PHANTOM")

    def run(self, setup=None):
        self._icon.run(setup=setup)

    def stop(self):
        self._icon.stop()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tray.py -v`
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add phantom/tray.py tests/test_tray.py
git commit -m "feat: add tray module with pystray icon and menu"
```

---

## Task 8: Hotkeys Module

**Files:**
- Create: `phantom/hotkeys.py`
- Create: `tests/test_hotkeys.py`

**Step 1: Write the failing tests**

```python
# tests/test_hotkeys.py
from unittest.mock import patch, MagicMock
import pytest
from phantom.hotkeys import HotkeyManager


@patch("phantom.hotkeys.keyboard")
def test_register_hotkeys(mock_kb):
    paste_cb = MagicMock()
    notes_cb = MagicMock()
    mgr = HotkeyManager()
    mgr.register("ctrl+shift+v", paste_cb)
    mgr.register("ctrl+shift+n", notes_cb)
    assert mock_kb.add_hotkey.call_count == 2


@patch("phantom.hotkeys.keyboard")
def test_unregister_all(mock_kb):
    mgr = HotkeyManager()
    mgr.register("ctrl+shift+v", MagicMock())
    mgr.unregister_all()
    mock_kb.unhook_all_hotkeys.assert_called_once()


@patch("phantom.hotkeys.keyboard")
def test_re_register_unregisters_first(mock_kb):
    mgr = HotkeyManager()
    mgr.register("ctrl+shift+v", MagicMock())
    mgr.register("ctrl+shift+v", MagicMock())
    # Should have removed the old one before adding new
    assert mock_kb.remove_hotkey.called
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hotkeys.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.hotkeys'`

**Step 3: Write minimal implementation**

```python
# phantom/hotkeys.py
import keyboard


class HotkeyManager:
    def __init__(self):
        self._hotkeys: dict[str, object] = {}

    def register(self, hotkey: str, callback):
        if hotkey in self._hotkeys:
            keyboard.remove_hotkey(self._hotkeys[hotkey])
        handle = keyboard.add_hotkey(hotkey, callback, suppress=True)
        self._hotkeys[hotkey] = handle

    def unregister_all(self):
        keyboard.unhook_all_hotkeys()
        self._hotkeys.clear()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_hotkeys.py -v`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add phantom/hotkeys.py tests/test_hotkeys.py
git commit -m "feat: add hotkeys module with keyboard library"
```

---

## Task 9: App Orchestrator — Mode 1 (Paste) End-to-End

**Files:**
- Create: `phantom/app.py`
- Create: `tests/test_app.py`

This is the main wiring. It connects all modules and runs the main event loop.

**Step 1: Write the failing tests**

```python
# tests/test_app.py
from unittest.mock import patch, MagicMock, PropertyMock
import numpy as np
import threading
import pytest


@patch("phantom.app.TrayApp")
@patch("phantom.app.HotkeyManager")
@patch("phantom.app.Transcriber")
@patch("phantom.app.Recorder")
@patch("phantom.app.Config")
@patch("phantom.app.History")
def test_app_creates_all_components(
    mock_history, mock_config, mock_recorder, mock_transcriber, mock_hotkeys, mock_tray
):
    from phantom.app import PhantomApp

    mock_config_inst = MagicMock()
    mock_config_inst.model_size = "base"
    mock_config_inst.mic_device = None
    mock_config_inst.hotkey_paste = "ctrl+shift+v"
    mock_config_inst.hotkey_notes = "ctrl+shift+n"
    mock_config.return_value = mock_config_inst

    app = PhantomApp.__new__(PhantomApp)
    app._init_components()

    mock_transcriber.assert_called_once_with(model_size="base")
    mock_recorder.assert_called_once()
    mock_hotkeys.assert_called_once()


@patch("phantom.app.paste_text")
@patch("phantom.app.Transcriber")
def test_process_paste_mode(mock_transcriber_cls, mock_paste):
    from phantom.app import PhantomApp

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = "Hello world"
    mock_transcriber_cls.return_value = mock_transcriber

    mock_history = MagicMock()
    mock_tray = MagicMock()

    audio = np.zeros((16000,), dtype=np.float32)

    # Test the processing directly
    PhantomApp._process_audio_static(audio, "paste", mock_transcriber, mock_history, mock_tray, None)

    mock_paste.assert_called_once_with("Hello world")
    mock_history.add.assert_called_once_with("Hello world", "paste")
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.app'` or import errors.

**Step 3: Write the app orchestrator**

```python
# phantom/app.py
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
        self._transcriber = Transcriber(model_size=self._config.model_size)
        self._hotkey_mgr = HotkeyManager()

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
        # Placeholder — will be implemented in Task 11
        logger.info("History requested (not yet implemented)")

    def _show_settings(self):
        # Placeholder — will be implemented in Task 12
        logger.info("Settings requested (not yet implemented)")

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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_app.py -v`
Expected: Both tests PASS.

**Step 5: Manual smoke test**

Run: `python -m phantom.app`
Expected: Tray icon appears in system tray. Right-click shows menu with History, Settings, Quit. Press Ctrl+Shift+V, speak, press again — text should paste. Press Quit to exit.

**Step 6: Commit**

```bash
git add phantom/app.py tests/test_app.py
git commit -m "feat: add app orchestrator with Mode 1 paste end-to-end"
```

---

## Task 10: Mode 2 (Voice Notes) Integration

Mode 2 is already wired in the orchestrator via the `_toggle_recording("notes")` path and `append_note`. This task is just verifying it works.

**Files:**
- Modify: `tests/test_app.py` (add Mode 2 test)

**Step 1: Add a Mode 2 test**

Add to `tests/test_app.py`:

```python
@patch("phantom.app.append_note")
@patch("phantom.app.Transcriber")
def test_process_notes_mode(mock_transcriber_cls, mock_append):
    from phantom.app import PhantomApp

    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = "Buy groceries"
    mock_transcriber_cls.return_value = mock_transcriber

    mock_history = MagicMock()
    mock_tray = MagicMock()

    from pathlib import Path
    notes_path = Path("/tmp/notes.md")

    PhantomApp._process_audio_static(
        audio=None,
        mode="notes",
        transcriber=None,
        history=mock_history,
        tray=mock_tray,
        notes_path=notes_path,
        text="Buy groceries",
    )

    mock_append.assert_called_once_with("Buy groceries", notes_path)
    mock_history.add.assert_called_once_with("Buy groceries", "notes")
```

**Step 2: Run tests**

Run: `pytest tests/test_app.py -v`
Expected: All 3 tests PASS.

**Step 3: Manual smoke test**

Run: `python -m phantom.app`
Press Ctrl+Shift+N, speak, press again. Check `~/phantom/notes.md` for the entry.

**Step 4: Commit**

```bash
git add tests/test_app.py
git commit -m "test: add Mode 2 notes integration test"
```

---

## Task 11: History UI (tkinter Dialog)

**Files:**
- Create: `phantom/ui/__init__.py`
- Create: `phantom/ui/history_window.py`
- Modify: `phantom/app.py` (wire up `_show_history`)

**Step 1: Write the history window**

```python
# phantom/ui/__init__.py
"""PHANTOM UI components."""
```

```python
# phantom/ui/history_window.py
import threading
import tkinter as tk
from tkinter import ttk

import pyperclip


class HistoryWindow:
    def __init__(self, history):
        self._history = history

    def show(self):
        """Open the history window. Must be called from a non-main thread."""
        thread = threading.Thread(target=self._build_window, daemon=True)
        thread.start()

    def _build_window(self):
        root = tk.Tk()
        root.title("PHANTOM - History")
        root.geometry("600x400")
        root.configure(bg="#2b2b2b")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#3c3f41", foreground="white",
                        fieldbackground="#3c3f41", rowheight=30)
        style.configure("Treeview.Heading", background="#2b2b2b",
                        foreground="white", font=("Segoe UI", 10, "bold"))

        tree = ttk.Treeview(root, columns=("time", "mode", "text"), show="headings")
        tree.heading("time", text="Time")
        tree.heading("mode", text="Mode")
        tree.heading("text", text="Text")
        tree.column("time", width=130, minwidth=130)
        tree.column("mode", width=60, minwidth=60)
        tree.column("text", width=400)

        scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        entries = self._history.get_all()
        entry_map = {}
        for entry in entries:
            preview = entry["text"][:80] + ("..." if len(entry["text"]) > 80 else "")
            iid = tree.insert("", "end", values=(entry["timestamp"], entry["mode"], preview))
            entry_map[iid] = entry

        def on_click(event):
            sel = tree.selection()
            if sel:
                entry = entry_map.get(sel[0])
                if entry:
                    pyperclip.copy(entry["text"])
                    status_var.set(f"Copied to clipboard: {entry['text'][:50]}...")

        tree.bind("<<TreeviewSelect>>", on_click)

        status_var = tk.StringVar(value="Click an entry to copy its text")
        status = tk.Label(root, textvariable=status_var, bg="#2b2b2b", fg="#aaaaaa",
                          anchor="w", padx=10)

        tree.pack(fill="both", expand=True, padx=5, pady=(5, 0))
        scrollbar.pack(side="right", fill="y")
        status.pack(fill="x", pady=(0, 5))

        root.mainloop()
```

**Step 2: Wire it into app.py**

In `phantom/app.py`, update the import and `_show_history` method:

Add import at top:
```python
from phantom.ui.history_window import HistoryWindow
```

Replace `_show_history`:
```python
    def _show_history(self):
        HistoryWindow(self._history).show()
```

**Step 3: Manual test**

Run the app, right-click tray → History. Window should open showing past entries.

**Step 4: Commit**

```bash
git add phantom/ui/__init__.py phantom/ui/history_window.py phantom/app.py
git commit -m "feat: add history viewer UI with tkinter"
```

---

## Task 12: Settings UI (tkinter Dialog)

**Files:**
- Create: `phantom/ui/settings_window.py`
- Modify: `phantom/app.py` (wire up `_show_settings`, handle model reload)

**Step 1: Write the settings window**

```python
# phantom/ui/settings_window.py
import threading
import tkinter as tk
from tkinter import ttk

import sounddevice as sd


class SettingsWindow:
    def __init__(self, config, on_save=None):
        self._config = config
        self._on_save = on_save

    def show(self):
        thread = threading.Thread(target=self._build_window, daemon=True)
        thread.start()

    def _build_window(self):
        root = tk.Tk()
        root.title("PHANTOM - Settings")
        root.geometry("450x320")
        root.configure(bg="#2b2b2b")
        root.resizable(False, False)

        fg = "white"
        bg = "#2b2b2b"
        entry_bg = "#3c3f41"
        font = ("Segoe UI", 10)

        row = 0
        tk.Label(root, text="Model Size:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        model_var = tk.StringVar(value=self._config.model_size)
        model_combo = ttk.Combobox(
            root, textvariable=model_var,
            values=["tiny", "base", "small", "medium"],
            state="readonly", width=20
        )
        model_combo.grid(row=row, column=1, padx=15, pady=10)

        row += 1
        tk.Label(root, text="Microphone:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        devices = sd.query_devices()
        input_devices = [(i, d["name"]) for i, d in enumerate(devices) if d["max_input_channels"] > 0]
        device_names = ["System Default"] + [name for _, name in input_devices]
        device_ids = [None] + [idx for idx, _ in input_devices]

        current_idx = 0
        if self._config.mic_device is not None:
            for i, did in enumerate(device_ids):
                if did == self._config.mic_device:
                    current_idx = i
                    break

        mic_var = tk.StringVar(value=device_names[current_idx])
        mic_combo = ttk.Combobox(
            root, textvariable=mic_var,
            values=device_names, state="readonly", width=30
        )
        mic_combo.grid(row=row, column=1, padx=15, pady=10)

        row += 1
        tk.Label(root, text="Paste Hotkey:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        paste_var = tk.StringVar(value=self._config.hotkey_paste)
        paste_entry = tk.Entry(root, textvariable=paste_var, bg=entry_bg, fg=fg,
                               insertbackground=fg, font=font, width=22)
        paste_entry.grid(row=row, column=1, padx=15, pady=10)

        row += 1
        tk.Label(root, text="Notes Hotkey:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        notes_var = tk.StringVar(value=self._config.hotkey_notes)
        notes_entry = tk.Entry(root, textvariable=notes_var, bg=entry_bg, fg=fg,
                               insertbackground=fg, font=font, width=22)
        notes_entry.grid(row=row, column=1, padx=15, pady=10)

        def on_save():
            self._config.model_size = model_var.get()
            mic_idx = device_names.index(mic_var.get())
            self._config.mic_device = device_ids[mic_idx]
            self._config.hotkey_paste = paste_var.get()
            self._config.hotkey_notes = notes_var.get()
            self._config.save()
            if self._on_save:
                self._on_save()
            root.destroy()

        row += 1
        tk.Button(root, text="Save", command=on_save, bg="#4a8c5c", fg="white",
                  font=font, width=15, relief="flat").grid(
            row=row, column=0, columnspan=2, pady=20
        )

        root.mainloop()
```

**Step 2: Wire it into app.py**

Add import at top of `phantom/app.py`:
```python
from phantom.ui.settings_window import SettingsWindow
```

Replace `_show_settings`:
```python
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
```

**Step 3: Manual test**

Run the app, right-click tray → Settings. Window should show dropdowns and text fields. Change a hotkey, save, verify new hotkey works.

**Step 4: Commit**

```bash
git add phantom/ui/settings_window.py phantom/app.py
git commit -m "feat: add settings UI with model, mic, and hotkey configuration"
```

---

## Task 13: Final Polish & Error Handling

**Files:**
- Modify: `phantom/app.py` (startup notifications, error handling)
- Modify: `phantom/tray.py` (mic status in menu)

**Step 1: Add startup notification for model download**

In `phantom/app.py`, in `_init_components`, wrap the transcriber creation:

```python
        try:
            self._tray.notify("Loading Whisper model...")
            self._transcriber = Transcriber(model_size=self._config.model_size)
        except Exception:
            logger.exception("Failed to load Whisper model")
            self._transcriber = None
```

**Step 2: Add mic availability check**

In `phantom/app.py`, add to `_toggle_recording`:

```python
        if self._transcriber is None:
            self._tray.notify("Whisper model not loaded")
            return
```

In `phantom/recorder.py`, wrap `start()` with try/except for sounddevice errors:

```python
    def start(self):
        self._chunks = []
        self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=self._device,
                callback=self._audio_callback,
            )
            self._stream.start()
        except sd.PortAudioError:
            self._recording = False
            raise
```

**Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS.

**Step 4: Full manual smoke test**

1. Run `python -m phantom.app`
2. Verify tray icon appears
3. Test Ctrl+Shift+V: record, stop, verify paste
4. Test Ctrl+Shift+N: record, stop, verify notes.md
5. Right-click → History: verify entries shown
6. Right-click → Settings: change a hotkey, save, verify
7. Right-click → Quit: verify clean exit

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add startup notifications and error handling polish"
```

---

## Summary of Build Order

| Task | Module | What it delivers |
|------|--------|-----------------|
| 0 | Environment | venv, deps, project scaffolding |
| 1 | config.py | JSON config load/save |
| 2 | history.py | SQLite CRUD, auto-pruning |
| 3 | notes.py | Markdown timestamped append |
| 4 | clipboard.py | Paste-to-focus |
| 5 | recorder.py | Audio capture with sounddevice |
| 6 | transcriber.py | faster-whisper inference |
| 7 | tray.py | System tray icon and menu |
| 8 | hotkeys.py | Global hotkey registration |
| 9 | app.py | Mode 1 end-to-end orchestration |
| 10 | tests | Mode 2 integration verification |
| 11 | history_window.py | History viewer UI |
| 12 | settings_window.py | Settings editor UI |
| 13 | Polish | Error handling, notifications |
