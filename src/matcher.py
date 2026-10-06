#!/usr/bin/env python3

import json
import re
from difflib import SequenceMatcher


MATCH_THRESHOLD = 0.85


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
    if not text:
        return set()

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

    except (TypeError, ValueError):
        return 0


def load_library(path="apple_music_library.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_best_match(song, library, threshold=MATCH_THRESHOLD):
    best = None
    best_score = 0

    for library_song in library:
        title = similarity(
            song.get("title", ""),
            library_song.get("title", "")
        )

        artist = artist_overlap(
            song.get("artist", ""),
            library_song.get("artist", "")
        )

        duration = duration_score(
            song.get("duration"),
            library_song.get("duration")
        )

        score = (
            title * 0.5 +
            artist * 0.3 +
            duration * 0.2
        )

        if score > best_score:
            best_score = score
            best = library_song

    confidence = round(best_score * 100, 2)
    matched = best is not None and best_score >= threshold

    result = {
        "matched": matched,
        "confidence": confidence
    }

    if best is not None:
        result["track_id"] = best.get("id")
        result["title"] = best.get("title")
        result["artist"] = best.get("artist")
        result["album"] = best.get("album")
        result["duration"] = best.get("duration")

    return result