import time

import pyautogui
import pyperclip


def paste_text(text: str):
    text = text.strip()
    if not text:
        return

    pyperclip.copy(text)
    time.sleep(0.1)  # Brief delay for clipboard reliability
    pyautogui.hotkey("ctrl", "v")
