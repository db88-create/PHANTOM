import keyboard


class HotkeyManager:
    def __init__(self):
        self._hotkeys: dict[str, object] = {}

    def register(self, hotkey: str, callback):
        if hotkey in self._hotkeys:
            keyboard.remove_hotkey(self._hotkeys[hotkey])
        handle = keyboard.add_hotkey(hotkey, callback, suppress=True)
        self._hotkeys[hotkey] = handle

    def unregister_all(self):
        keyboard.unhook_all_hotkeys()
        self._hotkeys.clear()
