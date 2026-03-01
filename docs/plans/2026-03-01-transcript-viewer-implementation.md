# Transcript Viewer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a floating transcript viewer window that shows the last 15 paste-mode transcriptions, with copy/paste buttons, always-on-top toggle, and hotkey/tray toggle visibility.

**Architecture:** A tkinter Toplevel window managed by `TranscriptViewer` class. The app orchestrator holds a reference and pushes new entries via callback after each paste transcription. The viewer runs its own tkinter mainloop on a daemon thread, using `root.after()` for thread-safe updates. The tray menu and a new hotkey (Ctrl+Shift+T) toggle visibility.

**Tech Stack:** tkinter (stdlib), pyperclip (existing), pyautogui (existing), no new dependencies.

---

## Task 1: Add `hotkey_transcript` to Config

**Files:**
- Modify: `phantom/config.py`
- Modify: `tests/test_config.py`

**Step 1: Add a test for the new default**

Add to `tests/test_config.py`:

```python
def test_default_config_has_transcript_hotkey(config_dir):
    cfg = Config(config_dir)
    assert cfg.hotkey_transcript == "ctrl+shift+t"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_default_config_has_transcript_hotkey -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'hotkey_transcript'`

**Step 3: Add the property to Config**

In `phantom/config.py`, add `"hotkey_transcript": "ctrl+shift+t"` to the `DEFAULTS` dict:

```python
DEFAULTS = {
    "model_size": "base",
    "mic_device": None,
    "hotkey_paste": "ctrl+shift+v",
    "hotkey_notes": "ctrl+shift+n",
    "hotkey_transcript": "ctrl+shift+t",
}
```

Add property and setter after the `hotkey_notes` property:

```python
    @property
    def hotkey_transcript(self) -> str:
        return self._data.get("hotkey_transcript", DEFAULTS["hotkey_transcript"])

    @hotkey_transcript.setter
    def hotkey_transcript(self, value: str):
        self._data["hotkey_transcript"] = value
```

Add `"hotkey_transcript": self.hotkey_transcript` to the `save()` payload dict.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add phantom/config.py tests/test_config.py
git commit -m "feat: add hotkey_transcript config property"
```

---

## Task 2: TranscriptViewer Widget

**Files:**
- Create: `phantom/ui/transcript_viewer.py`
- Create: `tests/test_transcript_viewer.py`

**Step 1: Write the failing tests**

```python
# tests/test_transcript_viewer.py
from unittest.mock import patch, MagicMock
import pytest
from phantom.ui.transcript_viewer import TranscriptViewer


def test_viewer_creation():
    mock_history = MagicMock()
    mock_history.get_all.return_value = []
    viewer = TranscriptViewer(mock_history)
    assert viewer is not None
    assert viewer._visible is False


def test_viewer_filters_paste_entries():
    mock_history = MagicMock()
    mock_history.get_all.return_value = [
        {"id": 3, "text": "Third paste", "mode": "paste", "timestamp": "2026-03-01 14:00:00"},
        {"id": 2, "text": "A note", "mode": "notes", "timestamp": "2026-03-01 13:30:00"},
        {"id": 1, "text": "First paste", "mode": "paste", "timestamp": "2026-03-01 13:00:00"},
    ]
    viewer = TranscriptViewer(mock_history)
    entries = viewer._get_paste_entries()
    assert len(entries) == 2
    assert entries[0]["text"] == "Third paste"
    assert entries[1]["text"] == "First paste"


def test_viewer_limits_to_15_entries():
    mock_history = MagicMock()
    mock_history.get_all.return_value = [
        {"id": i, "text": f"Entry {i}", "mode": "paste", "timestamp": f"2026-03-01 {i:02d}:00:00"}
        for i in range(20, 0, -1)
    ]
    viewer = TranscriptViewer(mock_history)
    entries = viewer._get_paste_entries()
    assert len(entries) == 15
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transcript_viewer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'phantom.ui.transcript_viewer'`

**Step 3: Write the TranscriptViewer class**

```python
# phantom/ui/transcript_viewer.py
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import pyperclip
import pyautogui

MAX_ENTRIES = 15


class TranscriptViewer:
    def __init__(self, history):
        self._history = history
        self._visible = False
        self._root = None
        self._cards_frame = None
        self._count_label = None
        self._entries: list[dict] = []
        self._on_top = False

    def _get_paste_entries(self) -> list[dict]:
        """Get the last MAX_ENTRIES paste-mode entries from history."""
        all_entries = self._history.get_all()
        paste_entries = [e for e in all_entries if e["mode"] == "paste"]
        return paste_entries[:MAX_ENTRIES]

    def start(self):
        """Start the viewer on a daemon thread. Window is hidden by default."""
        thread = threading.Thread(target=self._build_window, daemon=True)
        thread.start()

    def _build_window(self):
        self._root = tk.Tk()
        self._root.title("PHANTOM - Transcripts")
        self._root.geometry("400x500")
        self._root.configure(bg="#2b2b2b")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.withdraw()  # Start hidden

        fg = "white"
        bg = "#2b2b2b"
        font = ("Segoe UI", 10)

        # Toolbar
        toolbar = tk.Frame(self._root, bg=bg)
        toolbar.pack(fill="x", padx=10, pady=(8, 4))

        self._on_top_var = tk.BooleanVar(value=False)
        on_top_cb = tk.Checkbutton(
            toolbar, text="Always on Top", variable=self._on_top_var,
            command=self._toggle_on_top, fg=fg, bg=bg,
            selectcolor="#3c3f41", activebackground=bg,
            activeforeground=fg, font=font,
        )
        on_top_cb.pack(side="left")

        self._count_label = tk.Label(toolbar, text="0 entries", fg="#aaaaaa", bg=bg, font=font)
        self._count_label.pack(side="right")

        # Scrollable area
        container = tk.Frame(self._root, bg=bg)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self._cards_frame = tk.Frame(canvas, bg=bg)

        self._cards_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        self._canvas_window = canvas.create_window((0, 0), window=self._cards_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._canvas = canvas

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Load initial entries
        self._refresh_entries()

        self._root.mainloop()

    def _refresh_entries(self):
        """Reload all entries from history and rebuild cards."""
        if self._cards_frame is None:
            return

        for widget in self._cards_frame.winfo_children():
            widget.destroy()

        self._entries = self._get_paste_entries()
        self._update_count_label()

        for entry in self._entries:
            self._create_card(entry)

    def _create_card(self, entry: dict):
        """Create a single transcript card widget."""
        bg = "#3c3f41"
        fg = "white"
        font = ("Segoe UI", 10)
        font_small = ("Segoe UI", 8)

        card = tk.Frame(self._cards_frame, bg=bg, padx=10, pady=8)
        card.pack(fill="x", padx=5, pady=3)

        # Timestamp
        ts = entry.get("timestamp", "")
        tk.Label(card, text=ts, fg="#aaaaaa", bg=bg, font=font_small, anchor="w").pack(fill="x")

        # Text
        text = entry["text"]
        text_label = tk.Label(
            card, text=text, fg=fg, bg=bg, font=font,
            anchor="w", justify="left", wraplength=340,
        )
        text_label.pack(fill="x", pady=(2, 4))

        # Buttons
        btn_frame = tk.Frame(card, bg=bg)
        btn_frame.pack(fill="x")

        copy_btn = tk.Button(
            btn_frame, text="Copy", font=font_small,
            bg="#555555", fg=fg, relief="flat", padx=8, pady=2,
            command=lambda t=text: self._copy_text(t),
        )
        copy_btn.pack(side="left", padx=(0, 5))

        paste_btn = tk.Button(
            btn_frame, text="Paste", font=font_small,
            bg="#4a8c5c", fg=fg, relief="flat", padx=8, pady=2,
            command=lambda t=text: self._paste_text(t),
        )
        paste_btn.pack(side="left")

    def _copy_text(self, text: str):
        pyperclip.copy(text)

    def _paste_text(self, text: str):
        pyperclip.copy(text)
        import time
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")

    def _update_count_label(self):
        if self._count_label:
            n = len(self._entries)
            self._count_label.config(text=f"{n} entr{'y' if n == 1 else 'ies'}")

    def _toggle_on_top(self):
        if self._root:
            self._on_top = self._on_top_var.get()
            self._root.attributes("-topmost", self._on_top)

    def _on_close(self):
        """Hide instead of destroy on window X button."""
        self.hide()

    def toggle(self):
        """Toggle visibility. Thread-safe — can be called from any thread."""
        if self._root is None:
            return
        self._root.after(0, self._toggle_internal)

    def _toggle_internal(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self):
        """Show the window. Thread-safe."""
        if self._root is None:
            return
        self._root.after(0, self._show_internal)

    def _show_internal(self):
        self._refresh_entries()
        self._root.deiconify()
        self._visible = True

    def hide(self):
        """Hide the window. Thread-safe."""
        if self._root is None:
            return
        self._root.after(0, self._hide_internal)

    def _hide_internal(self):
        self._root.withdraw()
        self._visible = False

    def add_entry(self, text: str, timestamp: str):
        """Add a new entry and refresh. Thread-safe — called from transcription worker."""
        if self._root is None:
            return
        self._root.after(0, self._refresh_entries)
        # Scroll to top after refresh
        self._root.after(50, lambda: self._canvas.yview_moveto(0) if self._canvas else None)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transcript_viewer.py -v`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add phantom/ui/transcript_viewer.py tests/test_transcript_viewer.py
git commit -m "feat: add transcript viewer widget with copy/paste buttons"
```

---

## Task 3: Add "Transcripts" to Tray Menu

**Files:**
- Modify: `phantom/tray.py`
- Modify: `tests/test_tray.py`

**Step 1: Add a test for the new menu item**

Add to `tests/test_tray.py`:

```python
@patch("phantom.tray.pystray")
def test_tray_app_has_transcripts_callback(mock_pystray):
    callbacks = {
        "on_quit": MagicMock(),
        "on_history": MagicMock(),
        "on_settings": MagicMock(),
        "on_transcripts": MagicMock(),
    }
    tray = TrayApp(callbacks)
    tray._on_transcripts(MagicMock(), MagicMock())
    callbacks["on_transcripts"].assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_tray.py::test_tray_app_has_transcripts_callback -v`
Expected: FAIL — `AttributeError: 'TrayApp' object has no attribute '_on_transcripts'`

**Step 3: Add "Transcripts" to the tray menu**

In `phantom/tray.py`, update the `__init__` menu to insert "Transcripts" before "History":

```python
        self._icon = pystray.Icon(
            "phantom",
            icon=create_icon_image(recording=False),
            title="PHANTOM - Voice to Text",
            menu=pystray.Menu(
                pystray.MenuItem("Transcripts", self._on_transcripts),
                pystray.MenuItem("History", self._on_history),
                pystray.MenuItem("Settings", self._on_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._on_quit),
            ),
        )
```

Add the callback method:

```python
    def _on_transcripts(self, icon, item):
        cb = self._callbacks.get("on_transcripts")
        if cb:
            cb()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tray.py -v`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add phantom/tray.py tests/test_tray.py
git commit -m "feat: add Transcripts item to tray menu"
```

---

## Task 4: Wire Viewer into App Orchestrator

**Files:**
- Modify: `phantom/app.py`
- Modify: `tests/test_app.py`

**Step 1: Add a test for paste mode pushing to viewer**

Add to `tests/test_app.py`:

```python
@patch("phantom.app.paste_text")
@patch("phantom.app.Transcriber")
def test_process_paste_mode_notifies_viewer(mock_transcriber_cls, mock_paste):
    from phantom.app import PhantomApp

    mock_history = MagicMock()
    mock_tray = MagicMock()
    mock_viewer = MagicMock()

    PhantomApp._process_audio_static(
        audio=None,
        mode="paste",
        transcriber=None,
        history=mock_history,
        tray=mock_tray,
        notes_path=None,
        text="Hello viewer",
        transcript_viewer=mock_viewer,
    )

    mock_paste.assert_called_once_with("Hello viewer")
    mock_viewer.add_entry.assert_called_once()
    call_args = mock_viewer.add_entry.call_args
    assert call_args[0][0] == "Hello viewer"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py::test_process_paste_mode_notifies_viewer -v`
Expected: FAIL — `TypeError: _process_audio_static() got an unexpected keyword argument 'transcript_viewer'`

**Step 3: Wire the viewer into app.py**

In `phantom/app.py`, add import at top:

```python
from phantom.ui.transcript_viewer import TranscriptViewer
```

Update `_process_audio_static` signature to accept `transcript_viewer=None`:

```python
    @staticmethod
    def _process_audio_static(
        audio, mode, transcriber, history, tray, notes_path, text=None, transcript_viewer=None
    ):
        """Process transcribed audio. Static for testability."""
        if text is None:
            text = transcriber.transcribe(audio)

        if not text:
            return

        if mode == "paste":
            paste_text(text)
            if transcript_viewer is not None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                transcript_viewer.add_entry(text, timestamp)
        elif mode == "notes":
            append_note(text, notes_path)

        history.add(text, mode)
```

In `_init_components`, create the viewer after creating the tray:

```python
        self._transcript_viewer = TranscriptViewer(self._history)
```

Update the tray callbacks to include `on_transcripts`:

```python
        self._tray = TrayApp(
            callbacks={
                "on_quit": self._shutdown,
                "on_transcripts": self._toggle_transcripts,
                "on_history": self._show_history,
                "on_settings": self._show_settings,
            }
        )
```

Add `_toggle_transcripts` method:

```python
    def _toggle_transcripts(self):
        self._transcript_viewer.toggle()
```

In `_register_hotkeys`, add the transcript hotkey:

```python
        self._hotkey_mgr.register(
            self._config.hotkey_transcript, self._toggle_transcripts
        )
```

Update the log line:

```python
        logger.info(
            "Hotkeys registered: paste=%s, notes=%s, transcripts=%s",
            self._config.hotkey_paste,
            self._config.hotkey_notes,
            self._config.hotkey_transcript,
        )
```

In `_transcription_worker`, pass the viewer to `_process_audio_static`:

```python
                PhantomApp._process_audio_static(
                    audio=None,
                    mode=mode,
                    transcriber=None,
                    history=self._history,
                    tray=self._tray,
                    notes_path=self._config.data_dir / "notes.md",
                    text=text,
                    transcript_viewer=self._transcript_viewer,
                )
```

In `run()`, start the viewer before the tray:

```python
    def run(self):
        # Start transcript viewer (hidden by default)
        self._transcript_viewer.start()

        # Start transcription worker thread
        worker = threading.Thread(target=self._transcription_worker, daemon=True)
        worker.start()

        # Register hotkeys
        self._register_hotkeys()

        logger.info("PHANTOM is running. Press hotkeys to start recording.")

        # Run tray on main thread (blocks until quit)
        self._tray.run()
```

**Step 4: Run all tests to verify they pass**

Run: `pytest tests/ -v`
Expected: All tests PASS (including the new one).

**Step 5: Commit**

```bash
git add phantom/app.py tests/test_app.py
git commit -m "feat: wire transcript viewer into app orchestrator with hotkey and tray toggle"
```

---

## Summary

| Task | Files | What it delivers |
|------|-------|-----------------|
| 1 | config.py | `hotkey_transcript` config property |
| 2 | transcript_viewer.py | Floating viewer widget with copy/paste, always-on-top |
| 3 | tray.py | "Transcripts" tray menu item |
| 4 | app.py | Full wiring — viewer, hotkey, tray, auto-push on transcription |
