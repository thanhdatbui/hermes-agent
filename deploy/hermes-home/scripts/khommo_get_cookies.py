"""Lấy cookies khommo247 bằng Camoufox (chạy bằng venv-core024 — có camoufox).
In cookies ra stdout dạng "KHOMMO247SESSID_V2=...; cf_clearance=...".
"""
import sys, os, time, random, json

PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\khommo_profile")
PASS_PROXY = "TaadaaMobi#2026!"
PROXY_BASE = "test.taadaa.click"
MAX_PROXIES = 10

def main() -> int:
    from camoufox.sync_api import Camoufox

    proxies = [
        {"server": f"http://{PROXY_BASE}:{port}", "username": f"mobi{i}", "password": PASS_PROXY}
        for i, port in enumerate(range(5101, 5124), start=1)
    ]
    random.shuffle(proxies)

    for proxy in proxies[:MAX_PROXIES]:
        port = proxy["server"].split(":")[-1]
        try:
            with Camoufox(headless=False, proxy=proxy, geoip=False,
                          persistent_context=True, user_data_dir=PROFILE_DIR) as browser:
                page = browser.new_page()
                page.goto("https://khommo247.com/cong-cu/check-tiktok", wait_until="domcontentloaded", timeout=60000)
                cleared = False
                start = time.time()
                while time.time() - start < 60:
                    low = page.title().lower()
                    if "just a moment" not in low and "chờ một chút" not in low and not low.startswith("loading"):
                        cleared = True
                        break
                    page.wait_for_timeout(2000)
                if not cleared:
                    print(f"[cookies] {port} CF_BLOCK", file=sys.stderr, flush=True)
                    continue
                page.wait_for_timeout(3000)
                cookies = page.context.cookies()
                khommo = {c["name"]: c["value"] for c in cookies if "khommo" in c.get("domain", "")}
                sess = khommo.get("KHOMMO247SESSID_V2", "")
                cf = khommo.get("cf_clearance", "")
                if not sess:
                    print(f"[cookies] {port} thiếu SESSID", file=sys.stderr, flush=True)
                    continue
                header = f"KHOMMO247SESSID_V2={sess}; cf_clearance={cf}"
                os.makedirs(PROFILE_DIR, exist_ok=True)
                with open(os.path.join(PROFILE_DIR, "khommo_cookies.txt"), "w") as f:
                    f.write(header)
                print(header)
                return 0
        except Exception as e:
            print(f"[cookies] {port} EXC: {str(e)[:80]}", file=sys.stderr, flush=True)
            continue
    print("ERROR: không lấy được cookies", file=sys.stderr, flush=True)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())