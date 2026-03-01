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
