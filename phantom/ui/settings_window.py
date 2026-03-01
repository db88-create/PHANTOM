import threading
import tkinter as tk
from tkinter import ttk

import sounddevice as sd


class SettingsWindow:
    def __init__(self, config, on_save=None):
        self._config = config
        self._on_save = on_save

    def show(self):
        thread = threading.Thread(target=self._build_window, daemon=True)
        thread.start()

    def _build_window(self):
        root = tk.Tk()
        root.title("PHANTOM - Settings")
        root.geometry("450x320")
        root.configure(bg="#2b2b2b")
        root.resizable(False, False)

        fg = "white"
        bg = "#2b2b2b"
        entry_bg = "#3c3f41"
        font = ("Segoe UI", 10)

        row = 0
        tk.Label(root, text="Model Size:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        model_var = tk.StringVar(value=self._config.model_size)
        model_combo = ttk.Combobox(
            root, textvariable=model_var,
            values=["tiny", "base", "small", "medium"],
            state="readonly", width=20
        )
        model_combo.grid(row=row, column=1, padx=15, pady=10)

        row += 1
        tk.Label(root, text="Microphone:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        devices = sd.query_devices()
        input_devices = [(i, d["name"]) for i, d in enumerate(devices) if d["max_input_channels"] > 0]
        device_names = ["System Default"] + [name for _, name in input_devices]
        device_ids = [None] + [idx for idx, _ in input_devices]

        current_idx = 0
        if self._config.mic_device is not None:
            for i, did in enumerate(device_ids):
                if did == self._config.mic_device:
                    current_idx = i
                    break

        mic_var = tk.StringVar(value=device_names[current_idx])
        mic_combo = ttk.Combobox(
            root, textvariable=mic_var,
            values=device_names, state="readonly", width=30
        )
        mic_combo.grid(row=row, column=1, padx=15, pady=10)

        row += 1
        tk.Label(root, text="Paste Hotkey:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        paste_var = tk.StringVar(value=self._config.hotkey_paste)
        paste_entry = tk.Entry(root, textvariable=paste_var, bg=entry_bg, fg=fg,
                               insertbackground=fg, font=font, width=22)
        paste_entry.grid(row=row, column=1, padx=15, pady=10)

        row += 1
        tk.Label(root, text="Notes Hotkey:", fg=fg, bg=bg, font=font).grid(
            row=row, column=0, sticky="w", padx=15, pady=10
        )
        notes_var = tk.StringVar(value=self._config.hotkey_notes)
        notes_entry = tk.Entry(root, textvariable=notes_var, bg=entry_bg, fg=fg,
                               insertbackground=fg, font=font, width=22)
        notes_entry.grid(row=row, column=1, padx=15, pady=10)

        def on_save():
            self._config.model_size = model_var.get()
            mic_idx = device_names.index(mic_var.get())
            self._config.mic_device = device_ids[mic_idx]
            self._config.hotkey_paste = paste_var.get()
            self._config.hotkey_notes = notes_var.get()
            self._config.save()
            if self._on_save:
                self._on_save()
            root.destroy()

        row += 1
        tk.Button(root, text="Save", command=on_save, bg="#4a8c5c", fg="white",
                  font=font, width=15, relief="flat").grid(
            row=row, column=0, columnspan=2, pady=20
        )

        root.mainloop()
