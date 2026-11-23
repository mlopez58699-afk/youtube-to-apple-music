on run argv

    set jsonPath to item 1 of argv

    set songRecords to paragraphs of (do shell script "python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(chr(10).join((\"ID:\" + str(x[\"apple_music_id\"])) if x.get(\"apple_music_id\") else (\"FILE:\" + str(x[\"file\"])) for x in d[\"songs\"]))' " & quoted form of jsonPath)

    set playlistName to do shell script "python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[\"name\"])' " & quoted form of jsonPath

    tell application "Music"

        activate
        -- Check all songs before creating the playlist.
        repeat with songRecord in songRecords
            set songInfo to songRecord as text

            if songInfo starts with "ID:" then
                set trackID to text 4 thru -1 of songInfo
                set existingTrack to first track of library playlist 1 whose persistent ID is trackID

            else if songInfo starts with "FILE:" then
                set filePath to text 6 thru -1 of songInfo
                set fileAlias to (POSIX file filePath) as alias

            else
                error "Invalid song record: " & songInfo
            end if
        end repeat

        set newPlaylist to make new user playlist with properties {name:playlistName}

        repeat with songRecord in songRecords

            set songInfo to songRecord as text

            if songInfo starts with "ID:" then

                set trackID to text 4 thru -1 of songInfo

                set existingTrack to first track of library playlist 1 whose persistent ID is trackID

                duplicate existingTrack to newPlaylist

            else if songInfo starts with "FILE:" then

                set filePath to text 6 thru -1 of songInfo

                set fileAlias to (POSIX file filePath) as alias

                set importedTrack to add fileAlias

                duplicate importedTrack to newPlaylist

            end if

        end repeat

    end tell

end run