import threading
import tkinter as tk
from tkinter import ttk

import pyperclip


class HistoryWindow:
    def __init__(self, history):
        self._history = history

    def show(self):
        """Open the history window. Must be called from a non-main thread."""
        thread = threading.Thread(target=self._build_window, daemon=True)
        thread.start()

    def _build_window(self):
        root = tk.Tk()
        root.title("PHANTOM - History")
        root.geometry("600x400")
        root.configure(bg="#2b2b2b")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#3c3f41", foreground="white",
                        fieldbackground="#3c3f41", rowheight=30)
        style.configure("Treeview.Heading", background="#2b2b2b",
                        foreground="white", font=("Segoe UI", 10, "bold"))

        tree = ttk.Treeview(root, columns=("time", "mode", "text"), show="headings")
        tree.heading("time", text="Time")
        tree.heading("mode", text="Mode")
        tree.heading("text", text="Text")
        tree.column("time", width=130, minwidth=130)
        tree.column("mode", width=60, minwidth=60)
        tree.column("text", width=400)

        scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        entries = self._history.get_all()
        entry_map = {}
        for entry in entries:
            preview = entry["text"][:80] + ("..." if len(entry["text"]) > 80 else "")
            iid = tree.insert("", "end", values=(entry["timestamp"], entry["mode"], preview))
            entry_map[iid] = entry

        def on_click(event):
            sel = tree.selection()
            if sel:
                entry = entry_map.get(sel[0])
                if entry:
                    pyperclip.copy(entry["text"])
                    status_var.set(f"Copied to clipboard: {entry['text'][:50]}...")

        tree.bind("<<TreeviewSelect>>", on_click)

        status_var = tk.StringVar(value="Click an entry to copy its text")
        status = tk.Label(root, textvariable=status_var, bg="#2b2b2b", fg="#aaaaaa",
                          anchor="w", padx=10)

        tree.pack(fill="both", expand=True, padx=5, pady=(5, 0))
        scrollbar.pack(side="right", fill="y")
        status.pack(fill="x", pady=(0, 5))

        root.mainloop()
