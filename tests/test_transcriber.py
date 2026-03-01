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
