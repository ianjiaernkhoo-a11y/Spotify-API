#!/usr/bin/env bash
# Quick sanity check for SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET using the
# Client Credentials flow (no user login required). Verifies the app
# credentials work and can reach the Web API, using a public search call.
set -euo pipefail

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

: "${SPOTIFY_CLIENT_ID:?Set SPOTIFY_CLIENT_ID in .env or the environment}"
: "${SPOTIFY_CLIENT_SECRET:?Set SPOTIFY_CLIENT_SECRET in .env or the environment}"

echo "Requesting app access token..."
TOKEN_RESPONSE=$(curl -s -X POST https://accounts.spotify.com/api/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${SPOTIFY_CLIENT_ID}&client_secret=${SPOTIFY_CLIENT_SECRET}")

TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

if [ -z "$TOKEN" ]; then
  echo "Failed to get access token. Response was:"
  echo "$TOKEN_RESPONSE"
  exit 1
fi

echo "Got access token (length ${#TOKEN})."
echo "Searching for artist 'Radiohead'..."

curl -s -G "https://api.spotify.com/v1/search" \
  -H "Authorization: Bearer ${TOKEN}" \
  --data-urlencode "q=Radiohead" \
  --data-urlencode "type=artist" \
  --data-urlencode "limit=3" \
  | python3 -m json.tool
