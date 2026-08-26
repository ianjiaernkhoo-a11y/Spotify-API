# Spotify Now-Playing Dashboard — Project Spec

## Goal
Build a Raspberry Pi dashboard that shows the currently playing Spotify track
and song recommendations, using the Spotify Web API.

## Repo
`ianjiaernkhoo-a11y/Spotify-API`, branch `claude/spotify-api-access-ytloub`.

## Current state (already implemented)
- `requirements.txt` — `spotipy`, `python-dotenv`
- `.env.example` — template for `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`,
  `SPOTIFY_REDIRECT_URI`
- `.gitignore` — excludes `.env`, `.cache`, venv, pycache
- `auth.py` — builds an authenticated `spotipy.Spotify` client via
  `SpotifyOAuth` (Authorization Code flow), caching the token/refresh token
  to `.cache`. Requests scopes: `user-read-currently-playing`,
  `user-read-playback-state`, `user-read-recently-played`, `user-top-read`.
  Running it directly prints `Authenticated as: <name> (<id>)`.
- `now_playing.py` — polls `client.current_playback()` every 5s and prints
  the current track/artist/play-state when it changes.
- `test_credentials.sh` — sanity-checks `SPOTIFY_CLIENT_ID`/`SECRET` via the
  Client Credentials flow (no user login) by fetching an app token and
  running a sample artist search against `/v1/search`.
- `README.md` — setup steps (copy `.env.example` → `.env`, install deps,
  optionally run `test_credentials.sh`, run `auth.py` once, run
  `now_playing.py`).

## Spotify app setup (already done by user)
1. Created an app at https://developer.spotify.com/dashboard.
2. Redirect URI registered: `http://127.0.0.1:8888/callback` (Spotify
   requires `127.0.0.1`, not `localhost`, for loopback redirects).
3. Enabled "Web API" for the app.
4. Client ID and a Client Secret were generated.

**Security note:** an earlier Client ID/Secret pair was pasted into a chat
session and should be treated as compromised — **regenerate the Client
Secret** in the dashboard (Settings → Reset secret) before using it for real,
if that hasn't been done yet.

## Known environment constraint (why testing stalled remotely)
This work was being done inside a cloud/remote Claude Code session whose
outbound network policy blocks `accounts.spotify.com` and
`api.spotify.com` (confirmed via a 403 policy denial from the sandbox's
proxy). That environment also has no real browser, so the interactive
OAuth login step (visiting Spotify's login page and clicking "Agree")
could not be completed there either — that step inherently requires a
human, in a real browser, on a machine with working internet access.
**This is why the task is being continued in a local Claude Code session.**

## What's left to do (pick up here locally)
1. `cp .env.example .env` and fill in the (rotated) Client ID/Secret.
2. `pip install -r requirements.txt`.
3. Optionally run `./test_credentials.sh` to confirm the Client
   ID/Secret work (app-only token, no login).
4. Run `python auth.py` once — this opens a browser, you log in and
   approve, and it caches a token to `.cache`. Confirm it prints
   `Authenticated as: <name> (<id>)`.
5. Run `python now_playing.py` to confirm it prints the live currently
   playing track.
6. Design/build the actual dashboard UI for the Pi (not yet started) —
   options to consider: a local Flask/FastAPI web page shown in kiosk mode
   on a small screen, a terminal/TUI display, or a lightweight framebuffer
   app. Needs a decision on display hardware/resolution.
7. Add song recommendation logic. Note: Spotify deprecated the classic
   `/recommendations` endpoint for new API apps (Nov 2024) — recommendations
   will likely need to be built from `/me/top/tracks`, `/me/player/recently-played`,
   and/or audio-feature-based similarity, or a third-party
   recommendation approach. This needs research before implementing.
8. Deploy: get `.env` (with real values) and the cached `.cache` token onto
   the Pi itself, install deps there, and run the poller as a
   service/startup script.

## Open questions for the next session
- What display/hardware is the Pi driving (small HDMI screen, e-ink,
  touchscreen)? This determines whether the dashboard is a web page, a
  GUI toolkit app, or a TUI.
- Preferred recommendation approach, given the `/recommendations` endpoint
  deprecation.
- Whether Spotify Premium is available on the account (needed for any
  playback *control*, though read-only "currently playing" works on Free).
