import os

import requests
from flask import Flask, jsonify, render_template, request
from spotipy import SpotifyException

from auth import get_spotify_client
from lyrics import get_lyrics

app = Flask(__name__)
client = get_spotify_client()

VALID_TIME_RANGES = {"short_term", "medium_term", "long_term"}
VALID_SEARCH_TYPES = {"track", "artist", "album", "playlist"}

WALLPAPER_DIR = os.path.join(app.static_folder, "wallpapers")
WALLPAPER_EXTENSIONS = {".jpg", ".jpeg", ".jfif", ".png", ".webp", ".gif", ".svg"}

WEATHER_LATITUDE = os.environ.get("WEATHER_LATITUDE")
WEATHER_LONGITUDE = os.environ.get("WEATHER_LONGITUDE")
WEATHER_UNIT = os.environ.get("WEATHER_UNIT", "celsius")  # "celsius" or "fahrenheit"

# WMO weather codes (used by Open-Meteo) collapsed into a handful of emoji.
WEATHER_ICONS = {
    0: "☀️",  # clear sky
    1: "\U0001f324️",
    2: "⛅",
    3: "☁️",
    45: "\U0001f32b️",
    48: "\U0001f32b️",
    51: "\U0001f326️",
    53: "\U0001f326️",
    55: "\U0001f326️",
    61: "\U0001f327️",
    63: "\U0001f327️",
    65: "\U0001f327️",
    71: "\U0001f328️",
    73: "\U0001f328️",
    75: "\U0001f328️",
    80: "\U0001f326️",
    81: "\U0001f327️",
    82: "⛈️",
    95: "⛈️",
    96: "⛈️",
    99: "⛈️",
}


def api_error(exc: SpotifyException):
    return jsonify({"error": exc.msg or str(exc)}), exc.http_status or 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/kiosk")
def kiosk():
    return render_template("kiosk.html")


@app.route("/preview")
def preview():
    return render_template("preview.html")


@app.route("/wallpaper")
def wallpaper():
    return render_template("wallpaper.html")


@app.route("/api/wallpapers")
def wallpapers():
    try:
        names = sorted(os.listdir(WALLPAPER_DIR))
    except FileNotFoundError:
        return jsonify([])

    urls = [
        f"/static/wallpapers/{name}"
        for name in names
        if os.path.splitext(name)[1].lower() in WALLPAPER_EXTENSIONS
    ]
    return jsonify(urls)


@app.route("/api/now-playing")
def now_playing():
    playback = client.current_playback()
    if not playback or not playback.get("item"):
        return jsonify({"is_playing": False})

    item = playback["item"]
    images = item["album"]["images"]
    device = playback.get("device") or {}
    return jsonify(
        {
            "is_playing": playback["is_playing"],
            "track": item["name"],
            "artists": ", ".join(a["name"] for a in item["artists"]),
            "album": item["album"]["name"],
            "album_art": images[0]["url"] if images else None,
            "album_release_date": item["album"].get("release_date"),
            "album_release_date_precision": item["album"].get("release_date_precision"),
            "progress_ms": playback.get("progress_ms") or 0,
            "duration_ms": item.get("duration_ms") or 0,
            "device_name": device.get("name"),
            "volume_percent": device.get("volume_percent"),
            "shuffle_state": playback.get("shuffle_state"),
            "repeat_state": playback.get("repeat_state"),
        }
    )


@app.route("/api/lyrics")
def lyrics():
    playback = client.current_playback()
    if not playback or not playback.get("item"):
        return jsonify({"available": False})

    item = playback["item"]
    track_name = item["name"]
    artist_name = item["artists"][0]["name"] if item["artists"] else ""

    try:
        result = get_lyrics(track_name, artist_name)
    except requests.RequestException as exc:
        return jsonify({"available": False, "error": str(exc)})

    if result is None:
        return jsonify({"available": False})

    return jsonify({"available": True, **result})


@app.route("/api/track-extra")
def track_extra():
    playback = client.current_playback()
    if not playback or not playback.get("item"):
        return jsonify({"label": None})

    album_id = playback["item"]["album"]["id"]
    try:
        album = client.album(album_id)
    except SpotifyException as exc:
        return api_error(exc)

    return jsonify({"label": album.get("label")})


@app.route("/api/queue")
def queue():
    try:
        result = client.queue()
    except SpotifyException as exc:
        return api_error(exc)

    items = [
        {
            "track": t["name"],
            "artists": ", ".join(a["name"] for a in t["artists"]),
            "album_art": (t["album"]["images"] or [{}])[-1].get("url"),
        }
        for t in (result.get("queue") or [])[:3]
    ]
    return jsonify(items)


@app.route("/api/weather")
def weather():
    if not WEATHER_LATITUDE or not WEATHER_LONGITUDE:
        return jsonify({"configured": False})

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": WEATHER_LATITUDE,
                "longitude": WEATHER_LONGITUDE,
                "current": "temperature_2m,weather_code",
                "temperature_unit": WEATHER_UNIT,
                "timezone": "auto",
            },
            timeout=10,
        )
        response.raise_for_status()
        current = response.json()["current"]
    except (requests.RequestException, KeyError) as exc:
        return jsonify({"configured": True, "error": str(exc)}), 502

    return jsonify(
        {
            "configured": True,
            "temperature": current["temperature_2m"],
            "unit": "F" if WEATHER_UNIT == "fahrenheit" else "C",
            "icon": WEATHER_ICONS.get(current["weather_code"], "\U0001f321️"),
        }
    )


@app.route("/api/player/toggle", methods=["POST"])
def player_toggle():
    try:
        playback = client.current_playback()
        if playback and playback.get("is_playing"):
            client.pause_playback()
        else:
            client.start_playback()
        return jsonify({"ok": True})
    except SpotifyException as exc:
        return api_error(exc)


@app.route("/api/player/next", methods=["POST"])
def player_next():
    try:
        client.next_track()
        return jsonify({"ok": True})
    except SpotifyException as exc:
        return api_error(exc)


@app.route("/api/player/previous", methods=["POST"])
def player_previous():
    try:
        client.previous_track()
        return jsonify({"ok": True})
    except SpotifyException as exc:
        return api_error(exc)


@app.route("/api/player/shuffle", methods=["POST"])
def player_shuffle():
    state = bool((request.get_json(silent=True) or {}).get("state"))
    try:
        client.shuffle(state)
        return jsonify({"ok": True})
    except SpotifyException as exc:
        return api_error(exc)


@app.route("/api/player/volume", methods=["POST"])
def player_volume():
    volume = (request.get_json(silent=True) or {}).get("volume")
    try:
        client.volume(int(volume))
        return jsonify({"ok": True})
    except (SpotifyException, TypeError, ValueError) as exc:
        if isinstance(exc, SpotifyException):
            return api_error(exc)
        return jsonify({"error": "Invalid volume"}), 400


@app.route("/api/recently-played")
def recently_played():
    try:
        result = client.current_user_recently_played(limit=20)
    except SpotifyException as exc:
        return api_error(exc)

    items = [
        {
            "track": entry["track"]["name"],
            "artists": ", ".join(a["name"] for a in entry["track"]["artists"]),
            "album_art": (entry["track"]["album"]["images"] or [{}])[0].get("url"),
            "played_at": entry["played_at"],
        }
        for entry in result["items"]
    ]
    return jsonify(items)


@app.route("/api/top-tracks")
def top_tracks():
    time_range = request.args.get("time_range", "medium_term")
    if time_range not in VALID_TIME_RANGES:
        return jsonify({"error": "Invalid time_range"}), 400
    try:
        result = client.current_user_top_tracks(limit=10, time_range=time_range)
    except SpotifyException as exc:
        return api_error(exc)

    items = [
        {
            "track": t["name"],
            "artists": ", ".join(a["name"] for a in t["artists"]),
            "album_art": (t["album"]["images"] or [{}])[0].get("url"),
        }
        for t in result["items"]
    ]
    return jsonify(items)


@app.route("/api/top-artists")
def top_artists():
    time_range = request.args.get("time_range", "medium_term")
    if time_range not in VALID_TIME_RANGES:
        return jsonify({"error": "Invalid time_range"}), 400
    try:
        result = client.current_user_top_artists(limit=10, time_range=time_range)
    except SpotifyException as exc:
        return api_error(exc)

    items = [
        {
            "name": a["name"],
            "genres": ", ".join(a.get("genres", [])[:3]),
            "image": (a["images"] or [{}])[0].get("url"),
        }
        for a in result["items"]
    ]
    return jsonify(items)


@app.route("/api/playlists")
def playlists():
    try:
        result = client.current_user_playlists(limit=20)
    except SpotifyException as exc:
        return api_error(exc)

    items = [
        {
            "name": p["name"],
            "track_count": (p.get("tracks") or {}).get("total", 0),
            "image": (p["images"] or [{}])[0].get("url"),
            "owner": (p.get("owner") or {}).get("display_name", ""),
        }
        for p in result["items"]
        if p is not None
    ]
    return jsonify(items)


@app.route("/api/saved-tracks")
def saved_tracks():
    try:
        result = client.current_user_saved_tracks(limit=20)
    except SpotifyException as exc:
        return api_error(exc)

    items = [
        {
            "track": entry["track"]["name"],
            "artists": ", ".join(a["name"] for a in entry["track"]["artists"]),
            "album_art": (entry["track"]["album"]["images"] or [{}])[0].get("url"),
            "added_at": entry["added_at"],
        }
        for entry in result["items"]
    ]
    return jsonify(items)


@app.route("/api/followed-artists")
def followed_artists():
    try:
        result = client.current_user_followed_artists(limit=20)
    except SpotifyException as exc:
        return api_error(exc)

    items = [
        {
            "name": a["name"],
            "genres": ", ".join(a.get("genres", [])[:3]),
            "image": (a["images"] or [{}])[0].get("url"),
            "followers": (a.get("followers") or {}).get("total", 0),
        }
        for a in result["artists"]["items"]
    ]
    return jsonify(items)


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "track")
    if not query:
        return jsonify([])
    if search_type not in VALID_SEARCH_TYPES:
        return jsonify({"error": "Invalid type"}), 400

    try:
        result = client.search(q=query, type=search_type, limit=10)
    except SpotifyException as exc:
        return api_error(exc)

    key = f"{search_type}s"
    raw_items = result[key]["items"]

    if search_type == "track":
        items = [
            {
                "name": t["name"],
                "subtitle": ", ".join(a["name"] for a in t["artists"]),
                "image": (t["album"]["images"] or [{}])[0].get("url"),
            }
            for t in raw_items
        ]
    elif search_type == "artist":
        items = [
            {
                "name": a["name"],
                "subtitle": ", ".join(a.get("genres", [])[:3]),
                "image": (a["images"] or [{}])[0].get("url"),
            }
            for a in raw_items
        ]
    elif search_type == "album":
        items = [
            {
                "name": a["name"],
                "subtitle": ", ".join(ar["name"] for ar in a["artists"]),
                "image": (a["images"] or [{}])[0].get("url"),
            }
            for a in raw_items
        ]
    else:  # playlist
        items = [
            {
                "name": p["name"],
                "subtitle": p["owner"]["display_name"],
                "image": (p["images"] or [{}])[0].get("url"),
            }
            for p in raw_items
            if p is not None
        ]

    return jsonify(items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
