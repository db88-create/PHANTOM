import threading
import time
import tkinter as tk
from tkinter import ttk

import pyautogui
import pyperclip

MAX_ENTRIES = 15


class TranscriptViewer:
    def __init__(self, history):
        self._history = history
        self._visible = False
        self._root = None
        self._cards_frame = None
        self._count_label = None
        self._canvas = None
        self._canvas_window = None
        self._entries: list[dict] = []
        self._on_top = False

    def _get_paste_entries(self) -> list[dict]:
        """Get the last MAX_ENTRIES paste-mode entries from history."""
        all_entries = self._history.get_all()
        paste_entries = [e for e in all_entries if e["mode"] == "paste"]
        return paste_entries[:MAX_ENTRIES]

    def start(self):
        """Start the viewer on a daemon thread. Window is hidden by default."""
        thread = threading.Thread(target=self._build_window, daemon=True)
        thread.start()

    def _build_window(self):
        self._root = tk.Tk()
        self._root.title("PHANTOM - Transcripts")
        self._root.geometry("400x500")
        self._root.configure(bg="#2b2b2b")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.withdraw()  # Start hidden

        fg = "white"
        bg = "#2b2b2b"
        font = ("Segoe UI", 10)

        # Toolbar
        toolbar = tk.Frame(self._root, bg=bg)
        toolbar.pack(fill="x", padx=10, pady=(8, 4))

        self._on_top_var = tk.BooleanVar(value=False)
        on_top_cb = tk.Checkbutton(
            toolbar, text="Always on Top", variable=self._on_top_var,
            command=self._toggle_on_top, fg=fg, bg=bg,
            selectcolor="#3c3f41", activebackground=bg,
            activeforeground=fg, font=font,
        )
        on_top_cb.pack(side="left")

        self._count_label = tk.Label(toolbar, text="0 entries", fg="#aaaaaa", bg=bg, font=font)
        self._count_label.pack(side="right")

        # Scrollable area
        container = tk.Frame(self._root, bg=bg)
        container.pack(fill="both", expand=True, padx=5, pady=5)

        canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self._cards_frame = tk.Frame(canvas, bg=bg)

        self._cards_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        self._canvas_window = canvas.create_window((0, 0), window=self._cards_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._canvas = canvas

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Load initial entries
        self._refresh_entries()

        self._root.mainloop()

    def _refresh_entries(self):
        """Reload all entries from history and rebuild cards."""
        if self._cards_frame is None:
            return

        for widget in self._cards_frame.winfo_children():
            widget.destroy()

        self._entries = self._get_paste_entries()
        self._update_count_label()

        for entry in self._entries:
            self._create_card(entry)

    def _create_card(self, entry: dict):
        """Create a single transcript card widget."""
        bg = "#3c3f41"
        fg = "white"
        font = ("Segoe UI", 10)
        font_small = ("Segoe UI", 8)

        card = tk.Frame(self._cards_frame, bg=bg, padx=10, pady=8)
        card.pack(fill="x", padx=5, pady=3)

        # Timestamp
        ts = entry.get("timestamp", "")
        tk.Label(card, text=ts, fg="#aaaaaa", bg=bg, font=font_small, anchor="w").pack(fill="x")

        # Text
        text = entry["text"]
        text_label = tk.Label(
            card, text=text, fg=fg, bg=bg, font=font,
            anchor="w", justify="left", wraplength=340,
        )
        text_label.pack(fill="x", pady=(2, 4))

        # Buttons
        btn_frame = tk.Frame(card, bg=bg)
        btn_frame.pack(fill="x")

        copy_btn = tk.Button(
            btn_frame, text="Copy", font=font_small,
            bg="#555555", fg=fg, relief="flat", padx=8, pady=2,
            command=lambda t=text: self._copy_text(t),
        )
        copy_btn.pack(side="left", padx=(0, 5))

        paste_btn = tk.Button(
            btn_frame, text="Paste", font=font_small,
            bg="#4a8c5c", fg=fg, relief="flat", padx=8, pady=2,
            command=lambda t=text: self._paste_text(t),
        )
        paste_btn.pack(side="left")

    def _copy_text(self, text: str):
        pyperclip.copy(text)

    def _paste_text(self, text: str):
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")

    def _update_count_label(self):
        if self._count_label:
            n = len(self._entries)
            self._count_label.config(text=f"{n} entr{'y' if n == 1 else 'ies'}")

    def _toggle_on_top(self):
        if self._root:
            self._on_top = self._on_top_var.get()
            self._root.attributes("-topmost", self._on_top)

    def _on_close(self):
        """Hide instead of destroy on window X button."""
        self.hide()

    def toggle(self):
        """Toggle visibility. Thread-safe — can be called from any thread."""
        if self._root is None:
            return
        self._root.after(0, self._toggle_internal)

    def _toggle_internal(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self):
        """Show the window. Thread-safe."""
        if self._root is None:
            return
        self._root.after(0, self._show_internal)

    def _show_internal(self):
        self._refresh_entries()
        self._root.deiconify()
        self._visible = True

    def hide(self):
        """Hide the window. Thread-safe."""
        if self._root is None:
            return
        self._root.after(0, self._hide_internal)

    def _hide_internal(self):
        self._root.withdraw()
        self._visible = False

    def add_entry(self, text: str, timestamp: str):
        """Add a new entry and refresh. Thread-safe — called from transcription worker."""
        if self._root is None:
            return
        self._root.after(0, self._refresh_entries)
        # Scroll to top after refresh
        self._root.after(50, lambda: self._canvas.yview_moveto(0) if self._canvas else None)
