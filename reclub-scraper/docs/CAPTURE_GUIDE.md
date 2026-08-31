# Capturing ReClub's API traffic (Android)

ReClub has no public web API, so the practical way to find real endpoints is
to put your Android device/emulator's traffic through a proxy while you use
the app, then read the requests it makes. This only works for **your own
account**, at low volume, for personal use.

Android is the easier platform for this (no Mac, no code signing, and
rooting is much more accessible than iOS jailbreaking if you hit
certificate pinning), so it's the recommended target if the app is
available on both.

## 1. Set up mitmproxy on your computer

```bash
pip install mitmproxy
mitmweb --listen-port 8080
```

`mitmweb` opens a browser UI at http://127.0.0.1:8081 showing captured
traffic live. Note your computer's LAN IP — your phone/emulator needs it
next.

## 2. Get a device or emulator you can proxy

- **Emulator (recommended to start)**: create an AVD in Android Studio using
  a **Google APIs** system image (not "Google Play" — those images are
  harder to root). Google APIs images boot with a writable system
  partition, which you'll want in step 4 if pinning is an issue.
- **Physical device**: any Android phone works for basic proxying; you'll
  need it rooted (e.g. via Magisk) if you hit certificate pinning later.

Point its Wi-Fi (or the emulator's proxy setting, `-http-proxy` flag, or
`adb shell settings put global http_proxy <ip>:8080`) at your computer's
IP and port from step 1.

## 3. Install the mitmproxy certificate

1. With the proxy active, open the emulator/device's browser and go to
   `http://mitm.it`, then download the Android certificate.
2. Install it: **Settings → Security → Encryption & credentials → Install a
   certificate → CA certificate**, and select the downloaded file.

This gets you a **user-installed** certificate. That's often *not enough*
on its own — see the caveat in step 5.

## 4. Use the app and watch the traffic

Open ReClub and browse to club/event listings. In the mitmweb UI you'll see
each request. Look for calls to a domain that isn't Google/analytics/CDN —
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

## 5. If you see no traffic, or the app refuses to load data

Since Android 7 (API 24+), apps by default trust only **system** CAs, not
user-installed ones — so a user cert alone may not be enough even without
deliberate pinning. In order of effort:

1. **Push the mitmproxy CA into the system trust store** (needs root):
   ```bash
   adb root
   adb remount
   # move the cert from user store into /system/etc/security/cacerts/
   # with the correct filename (hash of the cert subject) and permissions
   ```
   This satisfies apps that trust "any system CA" but not apps doing true
   certificate pinning (checking the exact cert/public key).

2. **If ReClub pins its certificate**, use Frida + Objection on a rooted
   device/emulator to hook the app's TLS verification at runtime and force
   it to accept your proxy's cert regardless of pinning:
   ```bash
   pip install objection frida-tools
   # push frida-server matching your device's ABI/Frida version, run it as root
   objection -g com.reclub.app explore
   # inside objection:
   android sslpinning disable
   ```
   This is the Android equivalent of iOS jailbreak-based unpinning, but
   meaningfully easier to set up — rooting an emulator or a spare device via
   Magisk is routine.

3. **If none of that works**, the hidden-API approach is a dead end for now
   and Appium-based UI automation (driving the actual app screens via
   UiAutomator2) is the fallback — see `docs/APPIUM_ANDROID.md`.

## 6. Important caveats

- **Auth tokens expire.** Whatever `Authorization`/session token you copy
  out of the capture will likely expire (minutes to weeks depending on the
  app). `reclub_scraper.py` expects you to supply a fresh token via
  environment variable each time you run it, not a hardcoded one.
- **Personal, low-volume use only.** Keep request rates slow (the scraper
  defaults to a multi-second delay between calls) and only fetch what you
  actually need — this respects ReClub's infrastructure and keeps this
  squarely in "personal use" territory rather than bulk scraping.
