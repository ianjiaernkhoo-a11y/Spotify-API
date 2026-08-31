# Fallback: UI automation with Appium (Android)

Only needed if traffic capture (`CAPTURE_GUIDE.md`) is a dead end — e.g.
ReClub pins its certificate and Frida-based unpinning doesn't work on your
device. This drives the actual app screens instead of talking to its API
directly: slower and more fragile, but doesn't touch the network layer at
all, so pinning can't stop it.

## 1. Set up

Unlike iOS, this needs no Mac, no Xcode, no code signing — just:

```bash
pip install Appium-Python-Client
npm install -g appium
appium driver install uiautomator2
appium   # starts the Appium server on localhost:4723
```

Connect a device via USB with USB debugging enabled (Settings → Developer
options), or start an emulator — either way `adb devices` should list it.

## 2. Inspect the UI tree

Run **Appium Inspector** (separate GUI app) pointed at your running Appium
server to see the live view hierarchy while ReClub is open. Note each
element's `resource-id` (Android apps usually keep meaningful ones, e.g.
`com.reclub.app:id/club_name_text`) for the fields you want — these make
far more stable selectors than screen position or raw text matching.

## 3. Basic automation flow

```python
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
import time

options = UiAutomator2Options()
options.platform_version = "14"
options.device_name = "emulator-5554"       # from `adb devices`
options.app_package = "com.reclub.app"      # from the APK, or `adb shell pm list packages`
options.app_activity = ".MainActivity"      # from the APK manifest
options.no_reset = True                     # keep the existing logged-in session

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

# Navigate to the listings screen
driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Explore").click()

listings = []
seen = set()

while len(listings) < 200:
    cells = driver.find_elements(
        AppiumBy.ID, "com.reclub.app:id/club_list_item"
    )
    for cell in cells:
        name = cell.find_element(AppiumBy.ID, "com.reclub.app:id/club_name_text").text
        time_text = cell.find_element(AppiumBy.ID, "com.reclub.app:id/club_time_text").text
        key = (name, time_text)
        if key not in seen:
            seen.add(key)
            listings.append({"name": name, "time": time_text})

    size = driver.get_window_size()
    driver.swipe(size["width"] * 0.5, size["height"] * 0.8,
                 size["width"] * 0.5, size["height"] * 0.2, 800)
    time.sleep(2)   # pace scrolling — don't outrun the app's own loading

driver.quit()
```

Swap the `resource-id` strings for whatever Appium Inspector actually shows
you — the ones above are placeholders.

## 4. Notes

- If elements have no `resource-id` or accessibility label at all, you're
  reduced to matching by screen position or raw visible text, which breaks
  on any UI update — expect more maintenance than the API route.
- Same personal-use limits apply: pace scrolling like a human (the `sleep`
  calls above), don't run this continuously, and it's still scraping your
  own account's view of public listings, not bulk harvesting.
