import json
from pathlib import Path

DEFAULTS = {
    "model_size": "base",
    "mic_device": None,
    "hotkey_paste": "ctrl+shift+v",
    "hotkey_notes": "ctrl+shift+n",
}


class Config:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path.home() / "phantom"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self.data_dir / "config.json"
        self._data: dict = {}
        self._load()

    def _load(self):
        if self._config_path.exists():
            try:
                self._data = json.loads(self._config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def save(self):
        payload = {
            "model_size": self.model_size,
            "mic_device": self.mic_device,
            "hotkey_paste": self.hotkey_paste,
            "hotkey_notes": self.hotkey_notes,
        }
        self._config_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    @property
    def model_size(self) -> str:
        return self._data.get("model_size", DEFAULTS["model_size"])

    @model_size.setter
    def model_size(self, value: str):
        self._data["model_size"] = value

    @property
    def mic_device(self) -> int | None:
        return self._data.get("mic_device", DEFAULTS["mic_device"])

    @mic_device.setter
    def mic_device(self, value: int | None):
        self._data["mic_device"] = value

    @property
    def hotkey_paste(self) -> str:
        return self._data.get("hotkey_paste", DEFAULTS["hotkey_paste"])

    @hotkey_paste.setter
    def hotkey_paste(self, value: str):
        self._data["hotkey_paste"] = value

    @property
    def hotkey_notes(self) -> str:
        return self._data.get("hotkey_notes", DEFAULTS["hotkey_notes"])

    @hotkey_notes.setter
    def hotkey_notes(self, value: str):
        self._data["hotkey_notes"] = value
