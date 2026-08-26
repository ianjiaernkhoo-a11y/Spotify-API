"""Fetches lyrics via LRCLIB (https://lrclib.net) - a free, community-run
lyrics database. No API key or authentication required. Coverage is
crowd-sourced, so some tracks (especially very obscure ones) may be missing.
"""

import re

import requests

SEARCH_URL = "https://lrclib.net/api/search"

_LRC_LINE_RE = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$")


def _parse_synced_lyrics(lrc_text: str) -> list[dict]:
    lines = []
    for raw_line in lrc_text.splitlines():
        match = _LRC_LINE_RE.match(raw_line)
        if not match:
            continue
        minutes, seconds, text = match.groups()
        time_ms = int((int(minutes) * 60 + float(seconds)) * 1000)
        lines.append({"time_ms": time_ms, "text": text.strip()})
    return lines


def get_lyrics(track_name: str, artist_name: str) -> dict | None:
    """Returns {"sync_type": ..., "lines": [{"time_ms": int, "text": str}, ...]}
    or None if no match is found."""
    response = requests.get(
        SEARCH_URL,
        params={"track_name": track_name, "artist_name": artist_name},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None

    best = results[0]
    if best.get("instrumental"):
        return {"sync_type": "UNSYNCED", "lines": []}

    synced = best.get("syncedLyrics")
    if synced:
        return {"sync_type": "LINE_SYNCED", "lines": _parse_synced_lyrics(synced)}

    plain = best.get("plainLyrics")
    if plain:
        return {
            "sync_type": "UNSYNCED",
            "lines": [{"time_ms": 0, "text": line} for line in plain.split("\n") if line.strip()],
        }

    return None
