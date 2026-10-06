#!/usr/bin/env python3

import json
import re
import subprocess
import sys
from pathlib import Path
from mutagen import File

from matcher import load_library, find_best_match

def clean_youtube_artist(artist):
    if not artist:
        return ""

    artist = re.sub(r"\s+official$", "", artist, flags=re.IGNORECASE)
    artist = re.sub(r"\s*-\s*topic$", "", artist, flags=re.IGNORECASE)
    artist = re.sub(r"vevo$", "", artist, flags=re.IGNORECASE)

    return artist.strip()


def clean_youtube_title(title, artist=""):
    if not title:
        return ""

    cleaned = title.strip()

    # Remove artist prefix from titles such as:
    # "CUCO - Lava Lamp (Audio)"
    if " - " in cleaned:
        possible_artist, possible_title = cleaned.split(" - ", 1)

        if artist:
            normalized_artist = clean_youtube_artist(artist).lower()

            if (
                possible_artist.lower() in normalized_artist
                or normalized_artist in possible_artist.lower()
            ):
                cleaned = possible_title

    # Remove common YouTube video labels without stripping
    # meaningful parentheses from normal song titles.
    youtube_labels = [
        r"\(\s*official\s+4k\s+music\s+video\s*\)",
        r"\(\s*official\s+music\s+video\s*\)",
        r"\(\s*official\s+video\s*\)",
        r"\(\s*official\s+audio\s*\)",
        r"\(\s*audio\s*\)",
        r"\(\s*lyrics?\s*\)",
        r"\[\s*official\s+music\s+video\s*\]",
        r"\[\s*official\s+video\s*\]",
        r"\[\s*official\s+audio\s*\]",
        r"\[\s*audio\s*\]",
        r"\[\s*lyrics?\s*\]"
    ]

    for pattern in youtube_labels:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return " ".join(cleaned.split())

if len(sys.argv) != 2:
    print("Usage: ytmusic.py <YouTube playlist URL>")
    sys.exit(1)

url = sys.argv[1]

download_folder = Path.home() / "Downloads"

print("Loading Apple Music library...")

library = load_library()

print(f"Found {len(library)} tracks in Apple Music.")
print()

print("Reading YouTube playlist metadata...")

metadata_result = subprocess.run(
    [
        "yt-dlp",
        "--skip-download",
        "--dump-json",
        url
    ],
    capture_output=True,
    text=True
)

if metadata_result.returncode != 0:
    print("Could not read the complete YouTube playlist metadata.")
    print(metadata_result.stderr)
    sys.exit(1)

youtube_songs = []

for line in metadata_result.stdout.splitlines():
    if not line.strip():
        continue

    entry = json.loads(line)

    raw_title = entry.get("title", "")
    raw_artist = entry.get("artist")
    uploader = entry.get("uploader", "")

    artist = raw_artist or clean_youtube_artist(uploader)

    title = (
        entry.get("track")
        or clean_youtube_title(raw_title, artist)
    )

    youtube_songs.append({
        "title": title,
        "artist": artist,
        "duration": entry.get("duration"),
        "youtube_id": entry.get("id"),
        "url": entry.get("webpage_url"),
        "raw_title": raw_title
    })

print(f"Found {len(youtube_songs)} YouTube songs.")
print()

for song in youtube_songs:
    print(
        f'  {song["title"]} — '
        f'{song["artist"]} '
        f'({song["duration"]} sec)'
    )

print()

print("Downloading playlist...")

# Download playlist as ordered MP3 files
result = subprocess.run([
    "yt-dlp",
    "-f", "ba",
    "-x",
    "--audio-format", "mp3",
    "--audio-quality", "0",
    "--add-metadata",
    "--embed-thumbnail",
    "--convert-thumbnails", "jpg",
    "--ignore-errors",
    "-o",
    str(download_folder / "%(playlist)s/%(playlist_index)02d - %(title)s.%(ext)s"),
    url
])

if result.returncode != 0:
    print()
    print("⚠ Some songs could not be downloaded.")
    print("Continuing with the songs that were downloaded...")

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
