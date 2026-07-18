#!/usr/bin/env python3

import json
import re
from difflib import SequenceMatcher


def normalize(text):
    if not text:
        return ""

    text = text.lower()

    remove = [
        "feat.",
        "feat",
        "ft.",
        "ft",
        "with"
    ]

    for item in remove:
        text = text.replace(item, " ")

    text = re.sub(r"[^a-z0-9 ]", "", text)

    return " ".join(text.split())

def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize(a),
        normalize(b)
    ).ratio()


def split_artists(text):
    text = text.lower()

    separators = [
        " feat. ",
        " feat ",
        " ft. ",
        " ft ",
        " with ",
        "&",
        ","
    ]

    for sep in separators:
        text = text.replace(sep, ",")

    artists = text.split(",")

    cleaned = []

    for artist in artists:
        artist = re.sub(
            r"[^a-z0-9 ]",
            "",
            artist
        )

        artist = " ".join(artist.split())

        if artist:
            cleaned.append(artist)

    return set(cleaned)


def artist_overlap(a, b):

    a_artists = split_artists(a)
    b_artists = split_artists(b)

    if not a_artists:
        return 0

    matches = a_artists.intersection(b_artists)

    return len(matches) / len(a_artists)

def duration_score(a, b):
    try:
        difference = abs(float(a) - float(b))

        if difference <= 3:
            return 1

        if difference <= 8:
            return 0.75

        if difference <= 15:
            return 0.5

        return 0

    except:
        return 0


with open("apple_music_library.json", encoding="utf-8") as f:
    library = json.load(f)

test_song = {
    "title": "Good Flirts",
    "artist": "Baby Keem ft Kendrick Lamar",
    "duration": "232"
}

best = None
best_score = 0


for song in library:

    title = similarity(
        test_song["title"],
        song["title"]
    )

    artist = artist_overlap(
        test_song["artist"],
        song["artist"]
    )

    duration = duration_score(
        test_song["duration"],
        song["duration"]
    )


    score = (
        title * .5 +
        artist * .3 +
        duration * .2
    )


    if score > best_score:
        best_score = score
        best = song

print("Best Match:")
print(json.dumps(best, indent=2))

print()
print("Confidence:")
print(round(best_score * 100, 2), "%")


if best_score >= .85:
    print("MATCH CONFIRMED")
else:
    print("NO SAFE MATCH")
