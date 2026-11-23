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

if len(sys.argv) not in (2, 3) or (
    len(sys.argv) == 3 and sys.argv[2] != "--test-matches"
):

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
	"playlist_index": entry.get("playlist_index"),
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
print("Checking Apple Music library...")

matched_count = 0
missing_count = 0

for song in youtube_songs:
    match = find_best_match(song, library)

    song["matched"] = match["matched"]
    song["confidence"] = match["confidence"]

    if match["matched"] and match.get("track_id"):
        song["apple_music_id"] = match["track_id"]
        song["download"] = False

        matched_count += 1

        print(
            f'✓ {song["title"]} — already in Apple Music '
            f'({match["confidence"]}%)'
        )

    else:
        song["apple_music_id"] = None
        song["download"] = True

        missing_count += 1

        print(
            f'↓ {song["title"]} — needs downloading'
        )

print()
print(f"Already in Apple Music: {matched_count}")
print(f"Need to download: {missing_count}")
print()

if "--test-matches" in sys.argv:
    print("Test complete. No songs downloaded or imported.")
    sys.exit(0)

# Identify original playlist positions that need downloading.
# Verify original playlist positions before downloading.
for song in youtube_songs:
    if song["download"]:
        position = song.get("playlist_index")

        if not isinstance(position, int) or position < 1:
            print(f'ERROR: Invalid playlist position for {song["title"]}')
            print("No songs downloaded or imported.")
            sys.exit(1)
missing_positions = [
    str(song["playlist_index"])
    for song in youtube_songs
    if song["download"]
]

print("Preparing selective download...")
print(f"Songs requiring download: {len(missing_positions)}")

if missing_positions:
    playlist_items = ",".join(missing_positions)
    print(f"YouTube playlist positions: {playlist_items}")
else:
    playlist_items = ""
    print("All songs already exist in Apple Music.")
    print("No downloads are needed.")
    print()

print()

print()

if missing_positions:
    print("Downloading playlist...")

    # Download playlist as ordered MP3 files
    result = subprocess.run([
        "yt-dlp",
        "--playlist-items", playlist_items,
        "-f", "ba",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--add-metadata",
        "--embed-thumbnail",
        "--convert-thumbnails", "jpg",
        "-o",
        str(download_folder / "%(playlist)s/%(playlist_index)02d - %(title)s [%(id)s].%(ext)s"),
        url
    ])

    if result.returncode != 0:
        print()
        print("ERROR: The download process failed.")
        print("Playlist creation cancelled.")
        print("No changes were made to Apple Music.")
        sys.exit(1)

else:
    print("Skipping downloader: all songs already exist.")

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


# Find only MP3 files belonging to the current YouTube playlist.
files = []

for song in youtube_songs:
    if not song["download"]:
        continue

    youtube_id = song["youtube_id"]

    matches = [
        f for f in folder.glob("*.mp3")
        if f.name.endswith(f"[{youtube_id}].mp3")
    ]

    if len(matches) == 1:
        files.append(matches[0])
    elif len(matches) == 0:
        print(f'WARNING: No MP3 found for {song["title"]}')
    else:
        print(f'WARNING: Multiple MP3s found for {song["title"]}')

# Build the playlist in its original YouTube order.
songs = []
missing_files = []

for song in youtube_songs:

    if song["apple_music_id"]:
        songs.append({
            "title": song["title"],
            "artist": song["artist"],
            "apple_music_id": song["apple_music_id"],
            "file": None
        })
        continue

    youtube_id = song["youtube_id"]

    matches = [
        f for f in files
        if f.name.endswith(f"[{youtube_id}].mp3")
    ]

    if len(matches) != 1:
        missing_files.append(song["title"])
        continue

    f = matches[0]
    audio = File(f)

    songs.append({
        "file": str(f),
        "apple_music_id": None,
        "title": song["title"],
        "artist": song["artist"],
        "album": str(audio.get("TALB")[0])
        if audio and audio.get("TALB") else ""
    })

# Never import a partial playlist.
if missing_files:
    print()
    print("ERROR: Playlist creation cancelled.")
    print("Missing or ambiguous MP3 files:")
    for title in missing_files:
        print(f"  - {title}")
        print("No changes were made to Apple Music.")
    sys.exit(1)

folder.mkdir(parents=True, exist_ok=True)

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
