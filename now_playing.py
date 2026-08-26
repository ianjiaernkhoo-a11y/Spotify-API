import time

from auth import get_spotify_client

POLL_INTERVAL_SECONDS = 5


def format_track(playback: dict | None) -> str:
    if not playback or not playback.get("item"):
        return "Nothing is currently playing."

    item = playback["item"]
    artists = ", ".join(a["name"] for a in item["artists"])
    status = "Playing" if playback["is_playing"] else "Paused"
    return f"{status}: {item['name']} — {artists}"


def main() -> None:
    client = get_spotify_client()
    last_line = None

    while True:
        playback = client.current_playback()
        line = format_track(playback)
        if line != last_line:
            print(line)
            last_line = line
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
