# ReClub scraper (personal use)

ReClub is an iOS-only app with no public web API, so this fetches club/event
listing data by talking to the same backend API the app uses.

## How to use this

1. Read `docs/CAPTURE_GUIDE.md` and capture ReClub's API traffic from your
   own phone using mitmproxy. This tells you the real endpoint URL, request
   headers (including your auth token), and response JSON shape.
2. Install dependencies: `pip install -r requirements.txt`
3. Open `scripts/reclub_scraper.py` and adjust:
   - `LISTINGS_PATH`, the query params in `fetch_page`, and the field names
     in `extract_items` / `has_next_page` to match what you found in step 1.
4. Run it:
   ```bash
   export RECLUB_BASE_URL="https://api.reclubapp.example"
   export RECLUB_AUTH_TOKEN="<token from your capture>"
   python scripts/reclub_scraper.py --out listings.json --max-pages 5
   ```

## Scope and limits

- Built for **your own account**, at a slow, low-volume rate
  (`MIN_DELAY_SECONDS` in the script) — not for bulk/mass scraping.
- Your auth token will expire; re-run the capture to get a fresh one when
  requests start returning 401/403.
- If ReClub uses certificate pinning, traffic capture won't work at all
  (see the caveats section in `docs/CAPTURE_GUIDE.md`) and this approach
  would need to fall back to UI automation (Appium) instead.
