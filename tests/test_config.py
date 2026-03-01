import json
import os
import pytest
from phantom.config import Config


@pytest.fixture
def config_dir(tmp_path):
    """Use a temp directory instead of ~/phantom."""
    return tmp_path


def test_default_config_values(config_dir):
    cfg = Config(config_dir)
    assert cfg.model_size == "base"
    assert cfg.mic_device is None
    assert cfg.hotkey_paste == "ctrl+shift+v"
    assert cfg.hotkey_notes == "ctrl+shift+n"


def test_save_and_load_config(config_dir):
    cfg = Config(config_dir)
    cfg.model_size = "small"
    cfg.hotkey_paste = "ctrl+alt+v"
    cfg.save()

    cfg2 = Config(config_dir)
    assert cfg2.model_size == "small"
    assert cfg2.hotkey_paste == "ctrl+alt+v"
    # Unchanged values stay default
    assert cfg2.hotkey_notes == "ctrl+shift+n"


def test_creates_data_directory(tmp_path):
    data_dir = tmp_path / "phantom_data"
    cfg = Config(data_dir)
    assert data_dir.exists()


def test_handles_corrupted_config(config_dir):
    config_file = config_dir / "config.json"
    config_file.write_text("not valid json{{{")
    cfg = Config(config_dir)
    # Falls back to defaults
    assert cfg.model_size == "base"


def test_default_config_has_transcript_hotkey(config_dir):
    cfg = Config(config_dir)
    assert cfg.hotkey_transcript == "ctrl+shift+t"
