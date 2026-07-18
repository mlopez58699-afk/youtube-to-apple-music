on run argv
	
	set jsonPath to item 1 of argv
	
	set songFiles to paragraphs of (do shell script "python3 -c 'import json,sys; print(chr(10).join([x[\"file\"] for x in json.load(open(sys.argv[1]))[\"songs\"]]))' " & quoted form of jsonPath)
	
	set playlistName to do shell script "python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[\"name\"])' " & quoted form of jsonPath
	
	tell application "Music"
		activate
		
		set newPlaylist to make new user playlist with properties {name:playlistName}
		
		repeat with f in songFiles
			
			set fileAlias to (POSIX file (f as text)) as alias
			
			set importedTrack to add fileAlias
			
			duplicate importedTrack to newPlaylist
			
		end repeat
		
	end tell
	
end run
