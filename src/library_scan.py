#!/usr/bin/env python3

import subprocess
import json


applescript = r'''
tell application "Music"
	set output to ""
	
	repeat with t in tracks of library playlist 1
		
		try
			set trackName to name of t
			set trackArtist to artist of t
			set trackAlbum to album of t
			set trackDuration to duration of t
			set trackID to persistent ID of t
			
			set output to output & trackName & "|||" & trackArtist & "|||" & trackAlbum & "|||" & trackDuration & "|||" & trackID & linefeed
			
		end try
		
	end repeat
	
	return output
	
end tell
'''


print("Scanning Apple Music library...")


result = subprocess.check_output(
    ["osascript", "-e", applescript],
    text=True
)


songs = []


for line in result.splitlines():

    if "|||" not in line:
        continue

    parts = line.split("|||")

    if len(parts) == 5:
        songs.append({
            "title": parts[0],
            "artist": parts[1],
            "album": parts[2],
            "duration": parts[3],
            "id": parts[4]
        })


with open("apple_music_library.json", "w", encoding="utf-8") as f:
    json.dump(
        songs,
        f,
        indent=2,
        ensure_ascii=False
    )


print()
print(f"Found {len(songs)} tracks")
print("Saved apple_music_library.json")
