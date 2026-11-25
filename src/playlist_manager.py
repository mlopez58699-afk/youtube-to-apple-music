import subprocess


def find_existing_playlists(playlist_name):
    script = '''
    on run argv
        set targetName to item 1 of argv

        tell application "Music"
            set matchingPlaylists to every user playlist whose name is targetName
            set outputText to ""

            repeat with p in matchingPlaylists
                set outputText to outputText & ¬
                    (persistent ID of p) & tab & ¬
                    (count of tracks of p) & linefeed
            end repeat

            return outputText
        end tell
    end run
    '''

    result = subprocess.run(
        ["osascript", "-e", script, playlist_name],
        capture_output=True,
        text=True,
        check=True
    )

    playlists = []

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        playlist_id, song_count = line.split("\t")

        playlists.append({
            "name": playlist_name,
            "id": playlist_id,
            "song_count": int(song_count)
        })

    return playlists


def get_playlist_track_ids(playlist_id):
    script = '''
    on run argv
        set targetID to item 1 of argv

        tell application "Music"
            set targetPlaylist to first user playlist whose persistent ID is targetID
            set outputText to ""

            repeat with t in tracks of targetPlaylist
                set outputText to outputText & (persistent ID of t) & linefeed
            end repeat

            return outputText
        end tell
    end run
    '''

    result = subprocess.run(
        ["osascript", "-e", script, playlist_id],
        capture_output=True,
        text=True,
        check=True
    )

    return {
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    }
