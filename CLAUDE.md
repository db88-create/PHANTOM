# PHANTOM - Internal Development Reference

This document is a complete handoff for any AI assistant (or developer) picking up
PHANTOM development. It covers everything built, every decision made, every known
issue, and the full V2 backlog.

---

## What Is PHANTOM?

**Personal Hands-free Audio Notes & Text Output Machine**

A Windows desktop app that runs in the system tray and provides push-to-talk
voice-to-text. It uses OpenAI's Whisper model locally via `faster-whisper` — no
cloud, no API keys, fully offline.

**GitHub:** https://github.com/db88-create/PHANTOM
**License:** Free to use, no restrictions.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 (requires 3.11+) |
| ASR Engine | faster-whisper (CTranslate2 backend) |
| Audio Capture | sounddevice (PortAudio) |
| Hotkeys | keyboard (global, with `suppress=True`) |
| System Tray | pystray + Pillow |
| UI Windows | tkinter (dark theme, Segoe UI font) |
| Clipboard | pyperclip + pyautogui for Ctrl+V paste |
| Data Storage | SQLite (history.db), JSON (config.json), Markdown (notes.md) |
| Testing | pytest with unittest.mock |
| Package | pyproject.toml with `[project.scripts]` entry point |

**Venv location:** `C:\Users\Dbide\dev\PHANTOM\.venv`
**User data dir:** `~/phantom/` (i.e. `C:\Users\Dbide\phantom\`)
- `config.json` — runtime settings
- `history.db` — SQLite transcription history (50 entries max)
- `notes.md` — appended notes from notes mode

---

## Architecture

```
PhantomApp (app.py) — main orchestrator
  ├── Config (config.py) — loads/saves ~/phantom/config.json
  ├── History (history.py) — SQLite CRUD, 50-entry cap with auto-prune
  ├── Recorder (recorder.py) — sounddevice InputStream, 16kHz mono float32
  ├── Transcriber (transcriber.py) — faster-whisper, auto-detects CUDA/CPU
  ├── HotkeyManager (hotkeys.py) — wraps keyboard.add_hotkey with suppress
  ├── TrayApp (tray.py) — pystray icon with custom logo + recording dot overlay
  ├── TranscriptViewer (ui/transcript_viewer.py) — floating always-on-top viewer
  ├── HistoryWindow (ui/history_window.py) — ttk.Treeview browser
  └── SettingsWindow (ui/settings_window.py) — model, mic, hotkey editor
```

### Threading Model
- **Main thread:** pystray event loop (`TrayApp.run()`)
- **Daemon thread:** `_transcription_worker` — blocks on `queue.Queue`, transcribes audio, dispatches results
- **Daemon threads:** Each tkinter window (TranscriptViewer, HistoryWindow, SettingsWindow) runs its own `mainloop()` on a daemon thread
- **Thread safety:** TranscriptViewer uses `root.after(0, callback)` for cross-thread updates

### Recording Flow
1. User presses hotkey (e.g. `Ctrl+``)
2. `_toggle_recording("paste")` starts `Recorder.start()` which opens a sounddevice InputStream
3. TrayApp icon updates with red recording dot
4. User presses hotkey again
5. `Recorder.stop()` returns concatenated numpy audio array (discards if < 0.5s)
6. Audio + mode tuple pushed to `_work_queue`
7. Worker thread picks it up, calls `Transcriber.transcribe(audio)` (Whisper)
8. Result dispatched: paste mode → clipboard + auto-paste; notes mode → append to notes.md
9. History entry added to SQLite
10. TranscriptViewer notified (paste mode only)

---

## Current Hotkeys

| Hotkey | Action | Config Key |
|--------|--------|-----------|
| `Ctrl + `` | Toggle paste-mode recording | `hotkey_paste` |
| `Ctrl + 1` | Toggle notes-mode recording | `hotkey_notes` |
| `Ctrl + 2` | Toggle transcript viewer | `hotkey_transcript` |

These are the defaults in `config.py` AND the user's current `config.json`.

---

## File-by-File Reference

### phantom/app.py
Main orchestrator. Creates all components in `_init_components()`. Runs tray on
main thread. Transcription worker is a daemon thread reading from a Queue.
`_process_audio_static` is a `@staticmethod` for testability.

### phantom/recorder.py
Wraps `sounddevice.InputStream`. Records 16kHz mono float32. Collects chunks in
a callback, concatenates on stop. Returns `None` if duration < 0.5s.

### phantom/transcriber.py
Loads `faster-whisper` WhisperModel. Auto-detects CUDA via ctranslate2, falls
back to CPU with int8 quantization. Uses `beam_size=5` and `vad_filter=True`.

### phantom/clipboard.py
`paste_text(text)` — copies to clipboard via pyperclip, waits 100ms, then sends
Ctrl+V via pyautogui. This pastes into whatever window is currently focused.

### phantom/hotkeys.py
Thin wrapper around `keyboard` library. `suppress=True` prevents the hotkey from
reaching the active app. `unregister_all()` calls `keyboard.unhook_all_hotkeys()`.

### phantom/config.py
Manages `~/phantom/config.json`. Has property getters/setters for each config key
with defaults. `save()` writes all fields to disk.

### phantom/history.py
SQLite database at `~/phantom/history.db`. Table: `history(id, text, mode, timestamp)`.
Auto-prunes to 50 entries on each insert. `get_all()` returns newest first.

### phantom/notes.py
`append_note(text, path)` — appends a `## timestamp\ntext\n\n` entry to notes.md.
Uses Windows file locking (msvcrt) with fcntl fallback for cross-platform compat.

### phantom/tray.py
Loads `phantom_tray.png` from project root. Falls back to drawn gray circle if
file missing. When recording, overlays a red dot in bottom-right corner. Menu
items: Transcripts, History, Settings, Quit.

### phantom/ui/transcript_viewer.py
Floating dark-themed tkinter window. Shows last 15 paste-mode entries as cards
with Copy and Paste buttons. Always-on-top checkbox. Starts hidden, toggled via
hotkey or tray menu. `add_entry()` is thread-safe.

### phantom/ui/history_window.py
ttk.Treeview showing all history entries. Click to copy text to clipboard.

### phantom/ui/settings_window.py
Form for model size (combobox), microphone (queries sounddevice), paste hotkey,
notes hotkey. Save button writes config and triggers `_on_settings_saved` callback
which re-registers hotkeys.

### phantom.ico
Windows .ico file with multiple embedded sizes (256, 64, 48, 32, 16). Cropped
logo — hooded phantom figure only (no text). Used for desktop shortcut.

### phantom_tray.png
64x64 PNG of cropped logo. Loaded by tray.py at runtime.

---

## Tests

41 tests across 10 test files, all passing. Run with:
```bash
cd C:\Users\Dbide\dev\PHANTOM
.venv\Scripts\activate
pytest tests/ -v
```

| File | What It Tests |
|------|--------------|
| test_app.py | Component creation, paste/notes mode processing, viewer notification |
| test_clipboard.py | paste_text copies and triggers Ctrl+V |
| test_config.py | Defaults, load/save, property getters/setters |
| test_history.py | Add, get_all, get_by_id, prune logic |
| test_hotkeys.py | Register, unregister_all |
| test_notes.py | Append format, file creation, locking |
| test_recorder.py | Start/stop, min duration discard, callback |
| test_transcriber.py | Model loading, transcribe output |
| test_transcript_viewer.py | Viewer construction and methods |
| test_tray.py | Icon creation, recording dot, menu |

---

## Known Issues & Gotchas

### Windows Key Hotkeys Don't Work
The `keyboard` library can register `ctrl+windows+...` combos, but Windows OS
intercepts the Win key at a low level and the callback never fires. This was
tested and confirmed. **Do not use Win key in hotkey combos.**

### Windows Icon Cache
After changing `phantom.ico`, Windows aggressively caches the old icon. Tried:
- `ie4uinit.exe -show`
- Restarting Explorer (caused temporary RPC server unavailable errors)
- Deleting iconcache files from LocalAppData

None reliably worked. The workaround is: right-click shortcut > Properties >
Change Icon > browse to new .ico file. This is a Windows OS problem, not ours.

### Tray Icon Size
The phantom logo (hooded figure with audio wave bars) is too detailed to be
recognizable at 16-24px tray icon size. We crop out the "Phantom" text and just
use the figure, but it's still not great. Deferred to V2.

### Desktop Shortcut Path
The desktop path on this machine is `C:\Users\Dbide\OneDrive\Desktop`, NOT
`$env:USERPROFILE\Desktop`. Use `[Environment]::GetFolderPath('Desktop')` in
PowerShell to get the correct path.

### Settings Window Missing Transcript Hotkey
The SettingsWindow currently only shows paste and notes hotkey fields. It does
NOT include a field for the transcript viewer hotkey. Should be added.

### Model Reload
Changing the Whisper model in Settings doesn't hot-reload the model. User must
restart the app. This is by design for now (model loading is expensive).

---

## V2 Roadmap

### Recording Indicator Bubble (User's Primary V2 Request)
A small floating overlay that appears when recording is active, giving clear
visual feedback. The user described wanting:
- A small bubble/circle that pops up on screen when recording starts
- Disappears when recording stops
- Non-intrusive, doesn't steal focus
- Positioned somewhere visible but not in the way (e.g. top-right corner)
- Should show recording state (pulsing animation or red dot)

Implementation approach: A borderless, always-on-top, transparent tkinter window
with a small animated circle. Use `overrideredirect(True)` for no title bar,
`attributes('-alpha', 0.8)` for transparency, `attributes('-topmost', True)`.

### Icon Polish
The current logo doesn't scale well to small sizes. Options for V2:
- Design a simpler icon optimized for 16-32px (e.g. just the "P" or a
  simplified ghost shape)
- Use separate icons for tray vs desktop (already partially done)
- Consider SVG-to-ICO pipeline for crisp scaling

### PyInstaller Packaging
Currently requires Python + pip install. For distribution:
- `pyinstaller --onefile --windowed --icon=phantom.ico phantom/app.py`
- Bundle faster-whisper models or auto-download on first run
- This would make PHANTOM show up in Windows "Apps & Features"
- Consider creating an NSIS or Inno Setup installer

### Additional Ideas (Not Discussed, But Natural Extensions)
- Per-app paste mode (detect which app is focused, format accordingly)
- Audio feedback (beep on start/stop recording)
- Customizable transcript viewer position/size persistence
- Export history to CSV/JSON
- Multi-language support (Whisper supports many languages natively)
- GPU acceleration setup guide (CUDA + cuDNN for faster-whisper)

---

## How to Run

```bash
cd C:\Users\Dbide\dev\PHANTOM
.venv\Scripts\activate
phantom
```

Or without the entry point:
```bash
python -m phantom.app
```

Desktop shortcut exists at `C:\Users\Dbide\OneDrive\Desktop\PHANTOM.lnk`
pointing to `pythonw.exe -m phantom.app` (no console window).

---

## Git History Summary

```
44fd6a6 chore: update default hotkeys to ctrl+`, ctrl+1, ctrl+2
5d82337 docs: add README with usage, installation, and feature overview
e38113f chore: update icons with cropped logo (no text)
319e7a3 feat: replace programmatic tray icon with custom logo
457ef9a chore: add application icon
5bac8cc feat: wire transcript viewer into app orchestrator with hotkey and tray toggle
```

Earlier commits (from V1 build session) implemented the full 13-task plan:
recorder, transcriber, clipboard, hotkeys, config, history, notes, tray, settings
UI, history UI, app orchestrator, and all tests.
