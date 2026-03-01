# PHANTOM Design Document

Personal Voice-to-Text Engine for Windows.

## Overview

A lightweight Windows system tray application with two voice capture modes activated via global hotkeys. All transcription runs locally via faster-whisper with zero cloud dependencies.

## Modes

### Mode 1: Voice-to-Text Paste (Ctrl+Shift+V)

Press hotkey to start recording. Press again to stop. Audio is transcribed locally and the resulting text is pasted into whatever text field has focus. Entry saved to history.

### Mode 2: Voice Notes Capture (Ctrl+Shift+N)

Same record/stop flow. Instead of pasting, transcription is appended to `~/phantom/notes.md` with a timestamp header. Serves as an inbox for downstream AI agents. Entry saved to history.

## Tech Stack

- Python 3.11+
- faster-whisper (local Whisper ASR, CTranslate2 backend)
- keyboard (global hotkeys)
- sounddevice (audio recording, PortAudio-based)
- pystray (system tray integration)
- pyperclip + pyautogui (clipboard + paste simulation)
- SQLite (transcription history)
- Pillow (programmatic tray icon generation)

## Project Structure

```
phantom/
├── phantom/
│   ├── __init__.py
│   ├── app.py          # Entry point, orchestrator
│   ├── tray.py         # System tray icon, menu, state display
│   ├── hotkeys.py      # Global hotkey registration and dispatch
│   ├── recorder.py     # Audio capture via sounddevice
│   ├── transcriber.py  # faster-whisper model loading and inference
│   ├── clipboard.py    # Paste-to-focus (pyperclip + pyautogui)
│   ├── notes.py        # Markdown file append for Mode 2
│   ├── history.py      # SQLite history storage (last 50 entries)
│   └── config.py       # Config loading/saving
├── requirements.txt
└── pyproject.toml
```

Data directory: `~/phantom/` containing `notes.md`, `history.db`, `config.json`.

## Architecture: Multi-threaded

### Threads

- **Main thread**: pystray event loop (tray icon and menu)
- **Hotkey thread** (daemon): keyboard library listener, toggles recording state
- **Audio recording**: sounddevice callback-based, accumulates chunks into buffer
- **Transcription thread** (daemon): blocks on queue, runs faster-whisper, dispatches result

### Data Flow

1. Hotkey press toggles recording state
2. sounddevice callback accumulates 16kHz mono float32 audio chunks
3. On stop, concatenated audio array + mode placed on `queue.Queue`
4. Transcription thread picks up audio, runs faster-whisper
5. Mode 1: text → clipboard → simulated Ctrl+V paste
6. Mode 2: text → append to notes.md with timestamp
7. Both modes: entry saved to SQLite history

### Shared State

`AppState` dataclass with `recording: bool`, `current_mode: str`, protected by `threading.Lock`.

## Recording Details

- 16kHz mono float32 (Whisper's native format, no resampling needed)
- sounddevice.InputStream with callback-based chunk accumulation
- Recordings under 0.5 seconds discarded (accidental double-tap protection)
- Configured microphone; falls back to system default if disconnected

## Transcription Details

- faster-whisper model loaded once at startup, held in memory
- Auto-detects CUDA GPU; falls back to CPU with int8 quantization
- Default model: `base` (~150MB RAM, good speed/accuracy on CPU)
- Available models: tiny, base, small, medium (user configurable)
- Accepts numpy array directly (no temp files)
- Empty transcriptions (silence) discarded

## Paste Mechanism (Mode 1)

- Text set on clipboard via pyperclip
- 100ms delay for reliability
- pyautogui.hotkey('ctrl', 'v') simulates paste
- If no text field has focus, text remains on clipboard for manual paste

## Notes Mechanism (Mode 2)

- Append to `~/phantom/notes.md`
- Format: `## YYYY-MM-DD HH:MM` header followed by transcription text
- File locking to prevent corruption from rapid-fire notes

## System Tray

- Two icon states: idle (grey) and recording (red)
- Icons generated programmatically via Pillow (no external files)
- Right-click menu: History, Settings, Quit

## Settings (tkinter dialog)

- Model size: dropdown (tiny / base / small / medium)
- Microphone: dropdown (available input devices)
- Paste mode hotkey: text field (default: ctrl+shift+v)
- Notes mode hotkey: text field (default: ctrl+shift+n)
- Saved to `~/phantom/config.json`

## History (tkinter dialog)

- Scrollable list of last 50 entries
- Shows: timestamp, mode (paste/notes), truncated text preview
- Click entry to copy full text to clipboard
- Oldest entries auto-pruned when limit reached

## Config File

```json
{
  "model_size": "base",
  "mic_device": null,
  "hotkey_paste": "ctrl+shift+v",
  "hotkey_notes": "ctrl+shift+n"
}
```

`null` for mic_device means system default.

## Error Handling

- First launch: model download with tray notification
- No microphone: warning in tray menu, recording disabled until mic available
- Microphone disconnected mid-use: fallback to default, tray notification
- Transcription failure: logged, tray notification "Transcription failed"
- Missing data directory: created on first run

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Multi-threaded | Natural fit for concurrent tray + hotkeys + recording + transcription |
| Hotkey library | keyboard | Simpler API, reliable for Windows global hotkeys |
| Audio library | sounddevice | Clean callback API, actively maintained, numpy integration |
| Recording feedback | Tray icon color change only | Minimal, reliable, no extra windows |
| GPU detection | Auto-detect | Falls back gracefully to CPU with int8 quantization |
