from unittest.mock import patch, MagicMock
import pytest
from phantom.tray import create_icon_image, TrayApp


def test_create_icon_image_idle():
    img = create_icon_image(recording=False)
    assert img.size == (64, 64)


def test_create_icon_image_recording():
    img = create_icon_image(recording=True)
    assert img.size == (64, 64)


def test_create_icon_images_differ():
    idle = create_icon_image(recording=False)
    rec = create_icon_image(recording=True)
    # They should be different images (different colors)
    assert idle.tobytes() != rec.tobytes()


@patch("phantom.tray.pystray")
def test_tray_app_creation(mock_pystray):
    callbacks = {"on_quit": MagicMock(), "on_history": MagicMock(), "on_settings": MagicMock()}
    tray = TrayApp(callbacks)
    assert tray is not None


@patch("phantom.tray.pystray")
def test_tray_app_has_transcripts_callback(mock_pystray):
    callbacks = {
        "on_quit": MagicMock(),
        "on_history": MagicMock(),
        "on_settings": MagicMock(),
        "on_transcripts": MagicMock(),
    }
    tray = TrayApp(callbacks)
    tray._on_transcripts(MagicMock(), MagicMock())
    callbacks["on_transcripts"].assert_called_once()
