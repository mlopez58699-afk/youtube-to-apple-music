#!/usr/bin/env python3

import json
import re
import subprocess
import sys
from pathlib import Path
from mutagen import File

from matcher import load_library, find_best_match
from playlist_manager import find_existing_playlists, get_playlist_track_ids

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

print("Refreshing Apple Music library...")

scanner_path = Path(__file__).parent / "library_scan.py"

scan_result = subprocess.run(
    [sys.executable, str(scanner_path)]
)

if scan_result.returncode != 0:
    print()
    print("ERROR: Apple Music library scan failed.")
    print("No songs downloaded or imported.")
    sys.exit(1)

print()
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
playlist_name = None

for line in metadata_result.stdout.splitlines():
    if not line.strip():
        continue

    entry = json.loads(line)

    if not playlist_name:
        playlist_name = (
            entry.get("playlist")
            or entry.get("playlist_title")
        )

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

if not playlist_name or not youtube_songs:
    print("ERROR: Could not identify the playlist or its songs.")
    sys.exit(1)

print(f"Playlist: {playlist_name}")
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

# Detect existing Apple Music playlists.

print("Checking for existing Apple Music playlists...")

try:
    existing_playlists = find_existing_playlists(playlist_name)
except subprocess.CalledProcessError as error:
    print("ERROR: Could not check existing playlists.")
    print(error.stderr or str(error))
    sys.exit(1)

if existing_playlists:
    print(f"Found {len(existing_playlists)} existing playlist(s):")

    for playlist in existing_playlists:
        print(
            f'  {playlist["name"]} | '
            f'ID: {playlist["id"]} | '
            f'Songs: {playlist["song_count"]}'
        )
else:
    print("No existing playlists with this name.")

print()

# Select playlist action.

target_playlist_id = None

if existing_playlists:
    print("What would you like to do?")
    print("1. Add missing songs to an existing playlist")
    print("2. Create a new playlist")
    print("3. Cancel")

    choice = input("Enter your choice: ").strip()

    if choice == "1":
        print()
        print("Select a playlist to update:")

        for index, playlist in enumerate(existing_playlists, 1):
            print(
                f'{index}. {playlist["name"]} '
                f'({playlist["song_count"]} songs) '
                f'| ID: {playlist["id"]}'
            )

        selection = input("Select playlist number: ").strip()

        if not selection.isdigit():
            print("Invalid selection. Import cancelled.")
            sys.exit(1)

        index = int(selection) - 1

        if not 0 <= index < len(existing_playlists):
            print("Invalid selection. Import cancelled.")
            sys.exit(1)

        target_playlist_id = existing_playlists[index]["id"]

        print(f"Selected playlist ID: {target_playlist_id}")

    elif choice == "2":
        print("Create new playlist selected.")

    elif choice == "3":
        print("Import cancelled.")
        sys.exit(0)

    else:
        print("Invalid choice. Import cancelled.")
        sys.exit(1)

else:
    print("A new playlist will be created.")

# Filter songs already present in the selected playlist.

if target_playlist_id:
    print()
    print("Checking songs in the selected playlist...")

    try:
        existing_track_ids = get_playlist_track_ids(target_playlist_id)
    except subprocess.CalledProcessError as error:
        print("ERROR: Could not read the selected playlist.")
        print(error.stderr or str(error))
        sys.exit(1)

    songs_to_add = []
    skipped_count = 0
    duplicate_count = 0
    seen_track_ids = set()
    seen_youtube_ids = set()

    for song in youtube_songs:
        track_id = song.get("apple_music_id")
        youtube_id = song.get("youtube_id")

        if track_id and track_id in existing_track_ids:
            print(f'Already in playlist: {song["title"]}')
            skipped_count += 1
            continue

        if (
            (track_id and track_id in seen_track_ids)
            or (youtube_id and youtube_id in seen_youtube_ids)
        ):
            print(f'Duplicate in import: {song["title"]}')
            duplicate_count += 1
            continue

        songs_to_add.append(song)

        if track_id:
            seen_track_ids.add(track_id)

        if youtube_id:
            seen_youtube_ids.add(youtube_id)

        print(f'To be added: {song["title"]}')

    print(f"Repeated songs skipped: {duplicate_count}")

    youtube_songs = songs_to_add

    print()
    print(f"Songs already in playlist: {skipped_count}")
    print(f"New songs to add: {len(youtube_songs)}")
    print(f"Songs requiring download: {sum(s["download"] for s in youtube_songs)}")

# Finish early when the selected playlist is already up to date.

if target_playlist_id and not youtube_songs:
    print()
    print("Playlist is already up to date!")
    print("No songs needed to be added.")
    print("No changes were made to Apple Music.")
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

# Reuse the playlist name from the original metadata.


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

import_command = [
    "osascript",
    str(script_path),
    str(playlist_json)
]

if target_playlist_id:
    import_command.append(target_playlist_id)

result = subprocess.run(import_command)

if result.returncode == 0:
    print("Finished successfully!")
else:
    print()
    print("ERROR: Apple Music import failed.")
    print("Check Apple Music for a partially created playlist.")
    sys.exit(1)