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
