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

