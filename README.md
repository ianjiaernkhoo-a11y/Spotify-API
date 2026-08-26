# Spotify-API
Spotify API dashboard

## Setup

1. Create a Spotify app at https://developer.spotify.com/dashboard and note the
   Client ID, Client Secret, and add `http://127.0.0.1:8888/callback` as a
   Redirect URI.
2. Copy `.env.example` to `.env` and fill in your credentials:
   ```
   cp .env.example .env
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3b. (Optional) Sanity-check your Client ID/Secret before doing the full user
    login, using the Client Credentials flow (no browser needed):
   ```
   ./test_credentials.sh
   ```
4. Authenticate (opens a browser once to authorize your Spotify account, then
   caches a refresh token in `.cache`):
   ```
   python auth.py
   ```
5. Run the currently-playing poller:
   ```
   python now_playing.py
   ```
6. Or run the web dashboard, which demonstrates a broad set of Spotify Web
   API calls (now playing + playback controls, recently played, top
   tracks/artists, playlists, saved tracks, followed artists, search) plus
   a Lyrics tab:
   ```
   python dashboard.py
   ```
   Then open http://localhost:8080 (or the printed LAN address to view it
   from another device, e.g. a Pi's kiosk browser).

### Lyrics

There's no lyrics endpoint in the public Spotify Web API, so the dashboard's
Lyrics tab fetches from [LRCLIB](https://lrclib.net) — a free, community-run
lyrics database with no API key or account needed. It returns time-synced
lyrics when available (the tab highlights the current line as the track
plays) and falls back to plain text otherwise. Coverage is crowd-sourced, so
some obscure tracks may not have a match.

