from unittest.mock import patch, call
import pytest
from phantom.clipboard import paste_text


@patch("phantom.clipboard.pyautogui")
@patch("phantom.clipboard.pyperclip")
def test_paste_sets_clipboard_and_simulates_paste(mock_pyperclip, mock_pyautogui):
    paste_text("Hello world")
    mock_pyperclip.copy.assert_called_once_with("Hello world")
    mock_pyautogui.hotkey.assert_called_once_with("ctrl", "v")


@patch("phantom.clipboard.pyautogui")
@patch("phantom.clipboard.pyperclip")
def test_paste_empty_string_does_nothing(mock_pyperclip, mock_pyautogui):
    paste_text("")
    mock_pyperclip.copy.assert_not_called()
    mock_pyautogui.hotkey.assert_not_called()


@patch("phantom.clipboard.pyautogui")
@patch("phantom.clipboard.pyperclip")
def test_paste_strips_whitespace(mock_pyperclip, mock_pyautogui):
    paste_text("  Hello  ")
    mock_pyperclip.copy.assert_called_once_with("Hello")
