import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import re
import subprocess
import threading
import queue
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMPORTER = PROJECT_ROOT / "src" / "ytmusic.py"

events = queue.Queue()
running = False


ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def append_log(text):
    text = ANSI_PATTERN.sub("", text)
    log.configure(state="normal")
    log.insert("end", text)
    log.see("end")
    log.configure(state="disabled")


def run_importer(url, check_only):
    command = [
        sys.executable,
        "-u",
        str(IMPORTER),
        url
    ]

    if check_only:
        command.append("--test-matches")

    try:
        with subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        ) as process:

            for line in process.stdout:
                events.put(("log", line))

            return_code = process.wait()

        events.put(("done", return_code))

    except Exception as error:
        events.put(("log", f"\nError: {error}\n"))
        events.put(("done", 1))


def start_import(check_only=False):
    global running

    if running:
        return

    url = url_entry.get().strip()
    parsed = urlparse(url)

    if (
        parsed.scheme not in ("http", "https")
        or parsed.hostname not in (
            "youtube.com",
            "www.youtube.com",
            "music.youtube.com",
            "m.youtube.com"
        )
        or not parse_qs(parsed.query).get("list")
    ):
        messagebox.showwarning(
            "Invalid URL",
            "Please enter a valid YouTube playlist URL."
        )
        return

    running = True

    check_button.configure(state="disabled")
    import_button.configure(state="disabled")
    url_entry.configure(state="disabled")

    log.configure(state="normal")
    log.delete("1.0", "end")
    log.configure(state="disabled")

    status.configure(
        text="Checking playlist..." if check_only
        else "Importing playlist..."
    )

    progress.start(10)

    threading.Thread(
        target=run_importer,
        args=(url, check_only),
        daemon=True
    ).start()


def process_events():
    global running

    try:
        while True:
            event, value = events.get_nowait()

            if event == "log":
                append_log(value)

            elif event == "done":
                running = False
                progress.stop()

                check_button.configure(state="normal")
                import_button.configure(state="normal")
                url_entry.configure(state="normal")

                if value == 0:
                    status.configure(
                        text="Process completed successfully."
                    )
                else:
                    status.configure(
                        text="Process failed. Review the activity log."
                    )

    except queue.Empty:
        pass

    root.after(100, process_events)


def close_window():
    if running:
        messagebox.showinfo(
            "Process running",
            "Please wait for the current process to finish."
        )
    else:
        root.destroy()


root = tk.Tk()
root.title("YouTube to Apple Music")
root.geometry("720x540")
root.minsize(620, 460)
root.protocol("WM_DELETE_WINDOW", close_window)

frame = ttk.Frame(root, padding=25)
frame.pack(fill="both", expand=True)

ttk.Label(
    frame,
    text="YouTube to Apple Music",
    font=("Helvetica", 24, "bold")
).pack(pady=(0, 8))

ttk.Label(
    frame,
    text="Import your YouTube playlists into Apple Music."
).pack(pady=(0, 20))

ttk.Label(
    frame,
    text="YouTube Playlist URL"
).pack(anchor="w")

url_entry = ttk.Entry(frame)
url_entry.pack(fill="x", pady=(5, 15))

buttons = ttk.Frame(frame)
buttons.pack(pady=(0, 15))

check_button = ttk.Button(
    buttons,
    text="Check Playlist",
    command=lambda: start_import(True)
)
check_button.pack(side="left", padx=5)

import_button = ttk.Button(
    buttons,
    text="Import Playlist",
    command=lambda: start_import(False)
)
import_button.pack(side="left", padx=5)

progress = ttk.Progressbar(
    frame,
    mode="indeterminate"
)
progress.pack(fill="x", pady=(0, 15))

ttk.Label(
    frame,
    text="Activity Log"
).pack(anchor="w")

log = ScrolledText(
    frame,
    height=12,
    wrap="word",
    font=("Menlo", 11),
    state="disabled"
)
log.pack(fill="both", expand=True, pady=(5, 10))

status = ttk.Label(
    frame,
    text="Ready. Enter a YouTube playlist URL."
)
status.pack(anchor="w")

root.after(100, process_events)
root.mainloop()
