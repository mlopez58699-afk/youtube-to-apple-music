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

        set targetPlaylistID to ""

        if (count of argv) > 1 then
            set targetPlaylistID to item 2 of argv
        end if

        if targetPlaylistID is "" then
            set newPlaylist to make new user playlist with properties {name:playlistName}
        else
            set newPlaylist to first user playlist whose persistent ID is targetPlaylistID

            if (name of newPlaylist) is not playlistName then
                error "Selected playlist name has changed. Import cancelled."
            end if
        end if

        repeat with songRecord in songRecords

            set songInfo to songRecord as text

            if songInfo starts with "ID:" then

                set trackID to text 4 thru -1 of songInfo

                set existingTrack to first track of library playlist 1 whose persistent ID is trackID

                if targetPlaylistID is "" then
                    duplicate existingTrack to newPlaylist
                else
                    set matchingTracks to every track of newPlaylist whose persistent ID is trackID

                    if (count of matchingTracks) is 0 then
                        duplicate existingTrack to newPlaylist
                    end if
                end if

            else if songInfo starts with "FILE:" then

                set filePath to text 6 thru -1 of songInfo

                set fileAlias to (POSIX file filePath) as alias

                set importedTrack to add fileAlias

                duplicate importedTrack to newPlaylist

            end if

        end repeat

    end tell

end run