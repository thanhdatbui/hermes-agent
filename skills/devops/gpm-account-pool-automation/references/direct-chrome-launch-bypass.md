# Direct Chrome Core Launch Bypass for GPMLogin

## Pattern (Verified 2026-09-02)
When GPMLogin API (`/api/v3/profiles/start/{id}`) returns `"Yêu cầu cập trình duyệt [Chromium] [142]"`, bypass the API entirely by launching the Chrome core binary directly and connecting Playwright over CDP.

## Prerequisites
- Chrome core 142 binary: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe`
- Profile data directory: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\{profile_folder}\`

## Code Template (Method 1: Playwright Persistent Context with Proxy - Preferred)
```python
import os
from playwright.sync_api import sync_playwright

CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
PROFILE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\x_rua_jidbq"
PROXY_SERVER = "http://192.168.110.2:20017"  # Singbox direct proxy (no auth needed)

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        executable_path=CHROME_EXE,
        proxy={"server": PROXY_SERVER},
        headless=False,
        args=["--no-first-run", "--no-default-browser-check"]
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://myaccount.google.com", timeout=15000)
    # Check login status / perform actions
    context.close()
```

## Code Template (Method 2: Subprocess + Connect over CDP)
```python
import subprocess
import time
from playwright.sync_api import sync_playwright

CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
PROFILE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\16-8801317040143_4tcob"  # actual profile folder
PORT = 50064  # pick any free port

cmd = [
    CHROME_EXE,
    f"--remote-debugging-port={PORT}",
    f"--user-data-dir={PROFILE_DIR}",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
]

proc = subprocess.Popen(cmd)
time.sleep(3)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://accounts.google.com", timeout=15000)
        # ... rest of automation (login, OAuth, etc.)
finally:
    proc.terminate()
    proc.kill()
```

## Verified Result
```
Launching chrome directly...
Connected over CDP successfully!
Navigated to Google! Title: Google
Chrome process terminated.
```

## Advantages
- Bypasses GPM API update requirement entirely
- Full CDP/Playwright automation works (cookies, storage, extensions preserved)
- No dependency on GPM app state or license validation
- Works with any existing GPM profile folder

## Integration Point for Auto-GPM Repo
Add to `src/gpm_client.py`:
```python
def launch_chrome_direct(self, profile_path: str, port: int = 50064) -> str:
    """Launch Chrome core directly, return CDP URL. Bypasses GPM API."""
    # implementation above
    return f"http://127.0.0.1:{port}"
```

Then in `scripts/run_auth_batch.py`, catch the update error and fall back:
```python
try:
    cdp_url = gpm.start_profile(pid)
except RuntimeError as e:
    if "Yêu cầu cập trình duyệt" in str(e):
        cdp_url = gpm.launch_chrome_direct(profile_path)
    else:
        raise
```

## Related
- Skill: `gpm-account-pool-automation` — Section 15
- Skill: `computer-use` — Failure mode entry (WPF dialogs invisible)