from pathlib import Path

from PIL import Image, ImageDraw
import pystray

_ICON_PATH = Path(__file__).parent.parent / "phantom_tray.png"


def create_icon_image(recording: bool = False) -> Image.Image:
    size = 64

    # Load custom logo if available
    if _ICON_PATH.exists():
        img = Image.open(_ICON_PATH).resize((size, size), Image.LANCZOS).convert("RGBA")
    else:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, size - 8, size - 8], fill=(160, 160, 160, 255))
        center = size // 2
        r = 6
        draw.ellipse(
            [center - r, center - r, center + r, center + r], fill=(255, 255, 255, 255)
        )

    if recording:
        # Add red recording dot in bottom-right corner
        draw = ImageDraw.Draw(img)
        draw.ellipse([size - 22, size - 22, size - 4, size - 4], fill=(220, 50, 50, 255))

    return img


class TrayApp:
    def __init__(self, callbacks: dict):
        self._callbacks = callbacks
        self._icon = pystray.Icon(
            "phantom",
            icon=create_icon_image(recording=False),
            title="PHANTOM - Voice to Text",
            menu=pystray.Menu(
                pystray.MenuItem("Transcripts", self._on_transcripts),
                pystray.MenuItem("History", self._on_history),
                pystray.MenuItem("Settings", self._on_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._on_quit),
            ),
        )

    def _on_transcripts(self, icon, item):
        cb = self._callbacks.get("on_transcripts")
        if cb:
            cb()

    def _on_history(self, icon, item):
        cb = self._callbacks.get("on_history")
        if cb:
            cb()

    def _on_settings(self, icon, item):
        cb = self._callbacks.get("on_settings")
        if cb:
            cb()

    def _on_quit(self, icon, item):
        icon.stop()
        cb = self._callbacks.get("on_quit")
        if cb:
            cb()

    def set_recording(self, recording: bool):
        self._icon.icon = create_icon_image(recording=recording)

    def notify(self, message: str):
        self._icon.notify(message, "PHANTOM")

    def run(self, setup=None):
        self._icon.run(setup=setup)

    def stop(self):
        self._icon.stop()
