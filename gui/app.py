import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("YouTube to Apple Music")
root.geometry("520x260")
root.resizable(False, False)

frame = ttk.Frame(root, padding=25)
frame.pack(fill="both", expand=True)

title = ttk.Label(
    frame,
    text="YouTube to Apple Music",
    font=("Helvetica", 20, "bold")
)
title.pack(pady=(0, 10))

description = ttk.Label(
    frame,
    text="Import your YouTube playlists into Apple Music."
)
description.pack(pady=(0, 20))

url_entry = ttk.Entry(frame, width=60)
url_entry.pack(pady=(0, 15))

import_button = ttk.Button(
    frame,
    text="Import Playlist",
    state="disabled"
)
import_button.pack()

status = ttk.Label(
    frame,
    text="Interface preview — importing is not connected yet."
)
status.pack(pady=(20, 0))

root.mainloop()
