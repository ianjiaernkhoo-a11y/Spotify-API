import os

from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPES = " ".join(
    [
        "user-read-currently-playing",
        "user-read-playback-state",
        "user-read-recently-played",
        "user-top-read",
    ]
)


def get_spotify_client() -> Spotify:
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope=SCOPES,
        cache_path=".cache",
    )
    return Spotify(auth_manager=auth_manager)


if __name__ == "__main__":
    client = get_spotify_client()
    me = client.me()
    print(f"Authenticated as: {me['display_name']} ({me['id']})")
