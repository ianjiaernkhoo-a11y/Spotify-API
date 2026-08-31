#!/usr/bin/env python3
"""Fetch club/event listings from ReClub's API for personal use.

This is a template, not a finished scraper: the actual endpoint path,
query params, and response field names depend on what you find by
capturing the app's traffic (see docs/CAPTURE_GUIDE.md). Fill in the
constants below once you know them.

Usage:
    export RECLUB_BASE_URL="https://api.reclubapp.example"
    export RECLUB_LISTINGS_PATH="/v1/clubs"        # from your capture
    export RECLUB_AUTH_TOKEN="<token from the capture>"
    python reclub_scraper.py --out listings.json --max-pages 5
"""
import argparse
import json
import os
import sys
import time
from typing import Any

import requests

BASE_URL = os.environ.get("RECLUB_BASE_URL", "")
LISTINGS_PATH = os.environ.get("RECLUB_LISTINGS_PATH", "/v1/clubs")
AUTH_TOKEN = os.environ.get("RECLUB_AUTH_TOKEN", "")

# Minimum seconds to wait between requests. Keep this generous for personal,
# low-volume use rather than hammering the API.
MIN_DELAY_SECONDS = 3.0


def build_session() -> requests.Session:
    session = requests.Session()
    headers = {
        "User-Agent": "reclub-scraper/1.0 (personal use)",
        "Accept": "application/json",
    }
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    session.headers.update(headers)
    return session


def fetch_page(session: requests.Session, page: int) -> dict[str, Any]:
    url = f"{BASE_URL.rstrip('/')}{LISTINGS_PATH}"
    # Adjust these params to match whatever your traffic capture showed
    # (e.g. it might be `offset`/`limit`, or a cursor token, instead of `page`).
    params = {"page": page}
    response = session.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    # Adjust this key to match the real response shape from your capture.
    return payload.get("items", [])


def has_next_page(payload: dict[str, Any]) -> bool:
    # Adjust to match the real pagination signal (e.g. a `next_cursor`,
    # `has_more` flag, or comparing returned count to a page size).
    return bool(payload.get("has_more", False))


def scrape(max_pages: int) -> list[dict[str, Any]]:
    if not BASE_URL or not AUTH_TOKEN:
        print(
            "Set RECLUB_BASE_URL and RECLUB_AUTH_TOKEN (from your traffic "
            "capture) before running.",
            file=sys.stderr,
        )
        sys.exit(1)

    session = build_session()
    all_items: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        payload = fetch_page(session, page)
        items = extract_items(payload)
        if not items:
            break

        all_items.extend(items)
        print(f"Fetched page {page}: {len(items)} items (total {len(all_items)})")

        if not has_next_page(payload):
            break

        time.sleep(MIN_DELAY_SECONDS)

    return all_items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="listings.json", help="Output JSON file")
    parser.add_argument(
        "--max-pages", type=int, default=5, help="Maximum number of pages to fetch"
    )
    args = parser.parse_args()

    items = scrape(args.max_pages)

    with open(args.out, "w") as f:
        json.dump(items, f, indent=2)

    print(f"Wrote {len(items)} items to {args.out}")


if __name__ == "__main__":
    main()
