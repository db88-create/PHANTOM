from PIL import Image, ImageDraw
import pystray


def create_icon_image(recording: bool = False) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if recording:
        # Red circle when recording
        draw.ellipse([8, 8, size - 8, size - 8], fill=(220, 50, 50, 255))
    else:
        # Grey circle when idle
        draw.ellipse([8, 8, size - 8, size - 8], fill=(160, 160, 160, 255))

    # Inner "P" shape suggestion — small white dot
    center = size // 2
    r = 6
    draw.ellipse(
        [center - r, center - r, center + r, center + r], fill=(255, 255, 255, 255)
    )
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
