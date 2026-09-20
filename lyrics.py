"""Fetches lyrics via LRCLIB (https://lrclib.net) - a free, community-run
lyrics database. No API key or authentication required. Coverage is
crowd-sourced, so some tracks (especially very obscure ones) may be missing.
"""

import re
import time

import requests
from zhconv import convert as _zhconv

SEARCH_URL = "https://lrclib.net/api/search"
_RETRY_ATTEMPTS = 3
_RETRY_DELAY_S = 0.75

_LRC_LINE_RE = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$")


def _to_simplified(text: str) -> str:
    """LRCLIB returns whatever script the contributor uploaded (often
    Traditional for Chinese tracks). Converting to Simplified is a no-op
    for text that isn't Chinese, so this is safe to apply unconditionally."""
    return _zhconv(text, "zh-cn")


def _parse_synced_lyrics(lrc_text: str) -> list[dict]:
    lines = []
    for raw_line in lrc_text.splitlines():
        match = _LRC_LINE_RE.match(raw_line)
        if not match:
            continue
        minutes, seconds, text = match.groups()
        time_ms = int((int(minutes) * 60 + float(seconds)) * 1000)
        lines.append({"time_ms": time_ms, "text": _to_simplified(text.strip())})
    return lines


def _pick_best_match(results: list[dict], duration_ms: int | None) -> dict:
    """LRCLIB's search is fuzzy text matching, so the top hit can be a
    different version of the song (live, remix, extended cut) with its own
    timing — those have their own valid synced lyrics, just for a different
    runtime, which desyncs further as the track plays. Duration is a much
    stronger signal than search rank, so prefer whichever result's length
    actually matches what's playing.

    But duration proximity alone isn't enough: picking purely by closest
    duration can land on a result that only has plainLyrics (no timing at
    all) while a still-close-enough result has proper synced lyrics — that
    would trade "possibly slightly wrong version" for "definitely no
    highlighting whatsoever", which is worse. So prefer a synced result
    within LRCLIB's own ~2s duration tolerance first, and only fall back to
    picking by duration alone (synced or not) if none qualifies."""
    if duration_ms is None:
        return results[0]
    target_s = duration_ms / 1000

    def duration_diff(r):
        return abs((r.get("duration") or 0) - target_s)

    close_synced = [r for r in results if r.get("syncedLyrics") and duration_diff(r) <= 2]
    if close_synced:
        return min(close_synced, key=duration_diff)
    return min(results, key=duration_diff)


def _search(track_name: str, artist_name: str) -> list[dict]:
    """A single flaky connection (Pi WiFi) or a brief LRCLIB hiccup would
    otherwise surface as "lyrics unavailable" for the whole track with no
    second chance, so retry transient failures a couple of times before
    giving up."""
    last_exc = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            response = requests.get(
                SEARCH_URL,
                params={"track_name": track_name, "artist_name": artist_name},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < _RETRY_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY_S)
    raise last_exc


def get_lyrics(track_name: str, artist_name: str, duration_ms: int | None = None) -> dict | None:
    """Returns {"sync_type": ..., "lines": [{"time_ms": int, "text": str}, ...]}
    or None if no match is found. Pass the currently playing track's
    duration_ms so the right version/edit gets picked among search results."""
    results = _search(track_name, artist_name)
    if not results:
        return None

    best = _pick_best_match(results, duration_ms)
    if best.get("instrumental"):
        return {"sync_type": "UNSYNCED", "lines": []}

    synced = best.get("syncedLyrics")
    if synced:
        return {"sync_type": "LINE_SYNCED", "lines": _parse_synced_lyrics(synced)}

    plain = best.get("plainLyrics")
    if plain:
        return {
            "sync_type": "UNSYNCED",
            "lines": [
                {"time_ms": 0, "text": _to_simplified(line)}
                for line in plain.split("\n")
                if line.strip()
            ],
        }

    return None
