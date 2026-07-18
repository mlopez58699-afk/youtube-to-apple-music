#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path
from mutagen import File

if len(sys.argv) != 2:
    print("Usage: ytmusic.py <YouTube playlist URL>")
    sys.exit(1)

url = sys.argv[1]

download_folder = Path.home() / "Downloads"

print("Downloading playlist...")

# Download playlist as ordered MP3 files
subprocess.run([
    "yt-dlp",
    "-f", "ba",
    "-x",
    "--audio-format", "mp3",
    "--audio-quality", "0",
    "--add-metadata",
    "--embed-thumbnail",
    "--convert-thumbnails", "jpg",
    "-o",
    str(download_folder / "%(playlist)s/%(playlist_index)02d - %(title)s.%(ext)s"),
    url
], check=True)


# Get playlist name from yt-dlp
playlist_name = subprocess.check_output([
    "yt-dlp",
    "--print",
    "%(playlist)s",
    "--playlist-items",
    "1",
    url
]).decode().strip()


folder = download_folder / playlist_name

print("Reading metadata from:")
print(folder)


files = sorted(folder.glob("*.mp3"))

songs = []

for f in files:
    audio = File(f)

    songs.append({
        "file": str(f),
        "title": str(audio.get("TIT2")[0]) if audio.get("TIT2") else f.stem,
        "artist": str(audio.get("TPE1")[0]) if audio.get("TPE1") else "",
        "album": str(audio.get("TALB")[0]) if audio.get("TALB") else ""
    })


playlist_json = folder / "playlist.json"

with open(playlist_json, "w", encoding="utf-8") as f:
    json.dump(
        {
            "name": playlist_name,
            "songs": songs
        },
        f,
        indent=2,
        ensure_ascii=False
    )


print("Sending to Apple Music...")

script_path = Path(__file__).parent / "music_import.applescript"

result = subprocess.run([
    "osascript",
    str(script_path),
    str(playlist_json)
])

if result.returncode == 0:
    print("Finished successfully!")
else:
    print("Apple Music import failed.")
