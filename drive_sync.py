"""Pulls new photos from a shared Google Drive folder into static/wallpapers/,
so family can add photos to the frame from anywhere (not just the home WiFi
like the /upload page) by dropping them into that shared folder.

Run this file directly once to do the one-time browser login:
    python drive_sync.py

After that, call sync() periodically (e.g. from a systemd timer on the Pi,
same pattern as the git auto-update timer) — it reuses the stored token and
needs no further interaction.
"""

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from werkzeug.utils import secure_filename
import io

from image_utils import normalize_image

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Anchored to this file's own location (like Flask's app.static_folder is),
# not the current working directory — otherwise running this from anywhere
# other than the project root silently writes/reads the wrong place.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, ".drive_token.json")
WALLPAPER_DIR = os.path.join(BASE_DIR, "static", "wallpapers")
MANIFEST_PATH = os.path.join(WALLPAPER_DIR, ".drive_synced.json")

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}


def is_authenticated() -> bool:
    """True once the one-time terminal login (python drive_sync.py) has run.
    Callers that might run in a web request (no display to pop a browser on)
    should check this before calling sync()."""
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


def _load_manifest() -> dict:
    try:
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_manifest(manifest: dict) -> None:
    os.makedirs(WALLPAPER_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def sync() -> dict:
    """Downloads any Drive files not already synced. Returns a summary dict."""
    folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    service = build("drive", "v3", credentials=_get_credentials())
    manifest = _load_manifest()

    response = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)",
            pageSize=1000,
        )
        .execute()
    )
    drive_files = response.get("files", [])
    drive_ids = {f["id"] for f in drive_files}

    downloaded = []
    skipped = []

    for drive_file in drive_files:
        file_id = drive_file["id"]
        if file_id in manifest:
            continue  # already synced

        if drive_file.get("mimeType") not in IMAGE_MIME_TYPES:
            skipped.append({"name": drive_file["name"], "reason": "not a supported photo format"})
            continue

        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buffer.getvalue()

        try:
            data, converted = normalize_image(data)
        except ValueError:
            skipped.append({"name": drive_file["name"], "reason": "not a valid image"})
            continue

        safe_name = secure_filename(drive_file["name"]) or "photo"
        if converted:
            safe_name = os.path.splitext(safe_name)[0] + ".jpg"
        stored_name = f"gdrive-{file_id[:8]}-{safe_name}"
        with open(os.path.join(WALLPAPER_DIR, stored_name), "wb") as f:
            f.write(data)

        manifest[file_id] = stored_name
        downloaded.append(stored_name)

    # Drop manifest entries for files removed from the Drive folder, so a
    # re-add of the same file downloads it again instead of being skipped.
    for stale_id in list(manifest):
        if stale_id not in drive_ids:
            del manifest[stale_id]

    _save_manifest(manifest)
    return {"downloaded": downloaded, "skipped": skipped, "total_in_folder": len(drive_files)}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    result = sync()
    print(f"Downloaded {len(result['downloaded'])} new photo(s): {result['downloaded']}")
    if result["skipped"]:
        print(f"Skipped {len(result['skipped'])}: {result['skipped']}")
