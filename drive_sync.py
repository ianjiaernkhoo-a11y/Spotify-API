"""Streams photos live from a shared Google Drive folder so family can add
photos to the frame from anywhere (not just the home WiFi like the /upload
page) by dropping them into that shared folder — Drive stays the single
source of truth and nothing is written to the Pi's disk.

Run this file directly once to do the one-time browser login:
    python drive_sync.py

After that, list_photos() / get_photo_bytes() are called live on every
request (see dashboard.py) and just reuse the stored token.
"""

import io
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from image_utils import normalize_image

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Anchored to this file's own location (like Flask's app.static_folder is),
# not the current working directory — otherwise running this from anywhere
# other than the project root silently writes the token to the wrong place.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, ".drive_token.json")

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}

# In-memory only — a photo is fetched from Drive and converted (if HEIC) at
# most once per process lifetime, but nothing ever touches the Pi's disk.
_photo_cache: dict[str, tuple[bytes, str]] = {}


class DriveError(Exception):
    """Raised when a requested photo can't be served from Drive."""


def is_authenticated() -> bool:
    """True once the one-time terminal login (python drive_sync.py) has run.
    Callers that might run in a web request (no display to pop a browser on)
    should check this before calling list_photos()/get_photo_bytes()."""
    return os.path.exists(TOKEN_PATH)


def _get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        client_config = {
            "installed": {
                "client_id": os.environ["GOOGLE_DRIVE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_DRIVE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    return creds


def _service():
    return build("drive", "v3", credentials=_get_credentials())


def list_photos() -> list[dict]:
    """Live listing of supported photos in the shared Drive folder. Called
    on every /api/wallpapers request so newly-added Drive photos show up
    without any manual sync step."""
    folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    response = (
        _service()
        .files()
        .list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)",
            pageSize=1000,
        )
        .execute()
    )
    return [f for f in response.get("files", []) if f.get("mimeType") in IMAGE_MIME_TYPES]


def get_photo_bytes(file_id: str) -> tuple[bytes, str]:
    """Returns (bytes, content_type) for one photo, converting HEIC/HEIF to
    JPEG in memory since Chromium can't render it. Cached in RAM after the
    first fetch so rotating through the same photos doesn't re-hit Drive."""
    if file_id in _photo_cache:
        return _photo_cache[file_id]

    try:
        meta = _service().files().get(fileId=file_id, fields="mimeType").execute()
        request = _service().files().get_media(fileId=file_id)
    except Exception as exc:  # noqa: BLE001 - surface any Drive API error uniformly
        raise DriveError(str(exc)) from exc

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    data = buffer.getvalue()

    try:
        data, converted = normalize_image(data)
    except ValueError as exc:
        raise DriveError("not a valid image") from exc

    content_type = "image/jpeg" if converted else meta.get("mimeType", "image/jpeg")
    _photo_cache[file_id] = (data, content_type)
    return data, content_type


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    _get_credentials()
    photos = list_photos()
    print(f"Logged in. Drive folder has {len(photos)} photo(s) ready to stream.")
