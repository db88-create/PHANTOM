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
