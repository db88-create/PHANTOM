# PHANTOM

**Personal Hands-free Audio Notes & Text Output Machine**

A local voice-to-text engine for Windows. Press a hotkey, speak, and PHANTOM transcribes your speech using OpenAI's Whisper model running entirely on your machine. No cloud services, no subscriptions, no data leaving your computer.

## Features

- **Paste Mode** &mdash; Record speech and paste the transcription directly into any active text field
- **Notes Mode** &mdash; Dictate thoughts that get appended to a running notes file (`~/phantom/notes.md`)
- **Transcript Viewer** &mdash; Floating window that shows your recent transcriptions with one-click copy
- **History** &mdash; Browse all past transcriptions with timestamps
- **Settings UI** &mdash; Change Whisper model size, microphone, and hotkeys from the system tray
- **System Tray** &mdash; Runs quietly in your tray with a recording indicator dot
- **Fully Offline** &mdash; All processing happens locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)

## Requirements

- Windows 10/11
- Python 3.11+
- A working microphone

## Installation

```bash
git clone https://github.com/db88-create/PHANTOM.git
cd PHANTOM
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

On first run, Whisper will download the selected model (~150 MB for `base`).

## Usage

```bash
phantom
```

Or run directly:

```bash
python -m phantom.app
```

PHANTOM starts in the system tray. Use hotkeys to control it:

| Hotkey | Action |
|--------|--------|
| `Ctrl + `` | Toggle paste-mode recording |
| `Ctrl + 1` | Toggle notes-mode recording |
| `Ctrl + 2` | Toggle transcript viewer |

Hotkeys are fully configurable in **Settings** (right-click the tray icon).

## Configuration

Settings are stored in `~/phantom/config.json`:

```json
{
  "model_size": "base",
  "mic_device": null,
  "hotkey_paste": "ctrl+`",
  "hotkey_notes": "ctrl+1",
  "hotkey_transcript": "ctrl+2"
}
```

### Whisper Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~75 MB | Fastest | Basic |
| `base` | ~150 MB | Fast | Good |
| `small` | ~500 MB | Moderate | Better |
| `medium` | ~1.5 GB | Slow | Great |
| `large-v3` | ~3 GB | Slowest | Best |

## Project Structure

```
phantom/
  app.py            # Main application orchestrator
  recorder.py       # Microphone recording (sounddevice)
  transcriber.py    # Whisper transcription (faster-whisper)
  clipboard.py      # Paste-to-active-window
  hotkeys.py        # Global hotkey manager
  config.py         # Configuration management
  history.py        # Transcription history storage
  notes.py          # Notes file append
  tray.py           # System tray icon
  ui/
    transcript_viewer.py  # Floating transcript viewer
    history_window.py     # History browser
    settings_window.py    # Settings editor
```

## License

Free to use. Do whatever you want with it.
