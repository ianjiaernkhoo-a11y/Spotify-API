# Capturing ReClub's API traffic (iOS)

ReClub is iOS-only with no public web API, so the practical way to find real
endpoints is to put your iPhone's traffic through a proxy while you use the
app, then read the requests it makes. This only works for **your own
account**, at low volume, for personal use.

## 1. Set up mitmproxy on your computer

```bash
pip install mitmproxy
mitmweb --listen-port 8080
```

`mitmweb` opens a browser UI at http://127.0.0.1:8081 showing captured
traffic live. Note your computer's LAN IP (`ipconfig getifaddr en0` on Mac,
or check Wi-Fi settings) — your phone needs it in the next step.

## 2. Point your iPhone at the proxy

1. On the iPhone: **Settings → Wi-Fi → (i) next to your network → Configure
   Proxy → Manual**.
2. Server = your computer's LAN IP, Port = `8080`.
3. Make sure the phone and computer are on the **same Wi-Fi network**.

## 3. Install and trust the mitmproxy certificate

HTTPS traffic is encrypted, so mitmproxy needs a certificate your phone
trusts in order to decrypt and show it to you:

1. On the iPhone (while the proxy above is active), open Safari and go to
   `http://mitm.it`.
2. Tap the iOS certificate link and install the profile
   (**Settings → General → VPN & Device Management**).
3. Then go to **Settings → General → About → Certificate Trust Settings**
   and enable full trust for the "mitmproxy" certificate.

## 4. Use the app and watch the traffic

Open ReClub and browse to club/event listings. In the mitmweb UI you'll see
each request. Look for calls to a domain that isn't Apple/analytics/CDN —
that's ReClub's API. For each relevant request, note:

- Method + full URL (path and query params, e.g. `page`, `limit`, `city`)
- Request headers, especially `Authorization`, `Cookie`, or any custom
  `X-*` auth/session headers
- The JSON response shape (field names for club name, schedule, location,
  price, etc.)

`scripts/mitm_export.py` in this folder is an optional mitmproxy addon that
filters flows to a given host and dumps them to a JSON file, which is
easier to grep through than clicking every row in the UI:

```bash
mitmdump -s scripts/mitm_export.py --set target_host=api.reclubapp.example
```

## 5. Important caveats

- **Certificate pinning**: if the app pins its TLS certificate (rejects any
  cert other than the real server's, mitmproxy's included), you won't see
  decrypted traffic at all — the app will just fail to load data over the
  proxy. There's no simple non-jailbreak fix for this; if that happens, the
  hidden-API approach is a dead end and Appium-based UI automation (driving
  the actual app screens) would be the fallback instead.
- **Auth tokens expire.** Whatever `Authorization`/session token you copy
  out of the capture will likely expire (minutes to weeks depending on the
  app). `reclub_scraper.py` expects you to supply a fresh token via
  environment variable each time you run it, not a hardcoded one.
- **Personal, low-volume use only.** Keep request rates slow (the scraper
  defaults to a multi-second delay between calls) and only fetch what you
  actually need — this respects ReClub's infrastructure and keeps this
  squarely in "personal use" territory rather than bulk scraping.
