import asyncio
import json
import os
import sys
import subprocess
import time
import urllib.request
import urllib.parse
from pathlib import Path

CDP_HTTP = "http://127.0.0.1:9222"

def is_cdp_alive():
    try:
        with urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False

def get_browser_ws():
    try:
        with urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=3) as r:
            data = json.loads(r.read().decode('utf-8'))
            return data.get("webSocketDebuggerUrl")
    except Exception:
        return None

def get_open_tabs():
    try:
        with urllib.request.urlopen(f"{CDP_HTTP}/json/list", timeout=3) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:
        return []

def launch_chrome_cdp(target_url=None):
    if is_cdp_alive():
        print(f"[CDP] Chrome CDP is ALREADY RUNNING on {CDP_HTTP}")
        if target_url:
            open_tab(target_url)
        return True

    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    chrome_exe = None
    for c in chrome_candidates:
        if os.path.exists(c):
            chrome_exe = c
            break

    if not chrome_exe:
        print("[ERROR] chrome.exe not found on system!")
        return False

    user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data}",
        "--profile-directory=Profile 4",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    if target_url:
        cmd.append(target_url)

    print(f"[CDP] Launching Chrome CDP (Profile 4) with port 9222...")
    subprocess.Popen(cmd)
    
    for _ in range(15):
        time.sleep(0.5)
        if is_cdp_alive():
            print(f"[CDP] Successfully connected to Chrome CDP at {CDP_HTTP}!")
            return True

    print("[WARN] Chrome launched but port 9222 is not responding yet.")
    return False

def open_tab(url):
    import asyncio
    sys.path.insert(0, str(Path(__file__).parent))
    from cdp_eval import cdp_call

    b_ws = get_browser_ws()
    if not b_ws:
        print("[ERROR] Cannot get browser websocket URL")
        return None

    async def _create():
        res = await cdp_call(b_ws, "Target.createTarget", {"url": url})
        return res.get("result", {}).get("targetId") if res else None

    target_id = asyncio.run(_create())
    if target_id:
        print(f"[CDP] Opened new tab -> {url} (targetId: {target_id})")
        return target_id
    else:
        print(f"[ERROR] Failed to create target for {url}")
        return None

if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if not is_cdp_alive():
        launch_chrome_cdp(url_arg)
    else:
        print(f"[CDP] Chrome CDP (Profile 4) is currently ACTIVE at {CDP_HTTP}")
        tabs = get_open_tabs()
        pages = [t for t in tabs if t.get("type") == "page"]
        print(f"[CDP] Currently open pages ({len(pages)}):")
        for p in pages:
            print(f" - [{p.get('title')[:35]}] -> {p.get('url')[:60]}")
        if url_arg:
            open_tab(url_arg)
