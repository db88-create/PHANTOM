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
