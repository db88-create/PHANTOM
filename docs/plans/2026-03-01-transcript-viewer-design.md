# Transcript Viewer — Design

## Purpose

A small floating tkinter window showing the last 15 "paste" mode transcriptions. Auto-updates instantly via callback when new transcriptions arrive. Can toggle always-on-top, hide/show via tray menu or Ctrl+Shift+T hotkey.

## Window Layout

- **Title:** "PHANTOM - Transcripts"
- **Size:** ~400x500, resizable
- **Theme:** Dark, matching existing UI (#2b2b2b background, white text)
- **Top toolbar:** "Always on Top" checkbox, entry count label ("5 of 15")
- **Main area:** Scrollable list of transcript cards, newest at top
- **Each card:** Timestamp, transcript text, "Copy" button, "Paste" button
- **Auto-scrolls** to top when new entry arrives

## Behavior

- **On launch:** Loads last 15 "paste" entries from History DB
- **New transcription:** `app.py` calls `transcript_viewer.add_entry()` which inserts at top and trims to 15
- **Copy button:** Copies text to clipboard via pyperclip
- **Paste button:** Copies text to clipboard + simulates Ctrl+V into previously focused window
- **Always on Top checkbox:** Toggles `wm_attributes('-topmost')`
- **Ctrl+Shift+T or tray menu "Transcripts":** Toggles window visibility (hide/show, not destroy/recreate)
- **Window X button:** Hides instead of closing (withdraw)

## Integration with app.py

- `PhantomApp` creates `TranscriptViewer` at startup (hidden by default)
- New hotkey registered: `ctrl+shift+t` → toggle viewer visibility
- New tray menu item: "Transcripts" added between History and Settings
- After a "paste" mode transcription completes in `_process_audio_static`, calls `viewer.add_entry(text, timestamp)`
- Callback uses tkinter's `root.after()` for thread-safe UI updates from the transcription worker thread

## Architecture

- **File:** `phantom/ui/transcript_viewer.py`
- **Class:** `TranscriptViewer`
- **Dependencies:** tkinter (stdlib), pyperclip (existing), pyautogui (existing)
- **Thread safety:** Uses `root.after(0, callback)` to marshal updates onto the tkinter event loop from the transcription daemon thread
- **No new dependencies required**

## Tech Stack

Same as existing UI: tkinter + ttk, dark theme with Segoe UI font, pyperclip for clipboard, pyautogui for paste simulation.
