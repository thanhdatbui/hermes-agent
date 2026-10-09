"""
Scan GPM profiles to find ones with a live ChatGPT session.
Uses CDP cookie inspection to check for unified_session_manifest or
__Secure-next-auth.session-token — the signals that indicate an active
OpenAI/ChatGPT web session without needing to navigate pages.

Usage:
    python scan_gpm_live_chatgpt_sessions.py [--limit N] [--exclude EMAIL1,EMAIL2]

Output: list of (profile_id, email, machine, proxy) that are confirmed live.
Requires playwright and GPM running at localhost:19995.
"""

import urllib.request
import json
import asyncio
import sys

# farm state file — adjust path if needed
FARM_STATE = r"D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json"
GPM_API = "http://127.0.0.1:19995"

LIMIT = 10  # how many to find before stopping
ALREADY_IN_POOL = []  # emails already imported; set externally


def load_candidates():
    d = json.load(open(FARM_STATE, encoding="utf-8"))
    candidates = []
    for k, v in d.get("profiles", {}).items():
        if v.get("chatgpt_registered_at") and v.get("profile_id"):
            email = v.get("email", "")
            if email not in ALREADY_IN_POOL:
                candidates.append({
                    "pid": v["profile_id"],
                    "email": email,
                    "machine": v.get("machine"),
                    "proxy": v.get("proxy"),
                })
    return candidates


async def has_live_session(port: int) -> bool:
    from playwright.async_api import async_playwright
    live = False
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(
                f"http://127.0.0.1:{port}", timeout=8000
            )
            context = browser.contexts[0]
            cookies = await context.cookies()
            live = any(
                c["name"] in ("unified_session_manifest", "__Secure-next-auth.session-token.0")
                for c in cookies
            )
            await browser.close()
    except Exception:
        pass
    return live


async def scan(candidates, limit):
    from playwright.async_api import async_playwright  # noqa: ensure import
    results = []
    for c in candidates:
        pid = c["pid"]
        try:
            res = json.loads(
                urllib.request.urlopen(
                    f"{GPM_API}/api/v3/profiles/start/{pid}", timeout=20
                ).read().decode()
            )
            addr = res["data"]["remote_debugging_address"]
            port = int(addr.split(":")[-1])
            await asyncio.sleep(2)
            live = await has_live_session(port)
            urllib.request.urlopen(
                f"{GPM_API}/api/v3/profiles/close/{pid}", timeout=10
            )
            if live:
                print(f"LIVE: {c['email']} (machine {c['machine']}, pid {pid})")
                results.append(c)
                if len(results) >= limit:
                    break
            else:
                print(f"DEAD: {c['email']}")
        except Exception as e:
            print(f"ERROR {c['email']}: {e}")
    return results


if __name__ == "__main__":
    candidates = load_candidates()
    print(f"Total candidates to scan: {len(candidates)}")
    live = asyncio.run(scan(candidates, LIMIT))
    print(f"\nLive sessions found: {len(live)}")
    for c in live:
        print(f"  {c['pid']}  {c['email']}  machine={c['machine']}  proxy={c['proxy']}")
