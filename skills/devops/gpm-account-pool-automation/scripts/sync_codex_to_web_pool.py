#!/usr/bin/env python3
"""
Sync Codex Accounts from GPM Profiles to OmniRoute ChatGPT-Web Pool.
- Inspects connections in 'codex-terra-pool' and identifies accounts missing from 'chatgpt-web-pool'.
- Launches candidate GPM profiles with dual-stage teardown (API stop + psutil process tree kill).
- Navigates to chatgpt.com, removes the blocking static cookie consent banner via JS evaluation.
- Triggers the mobile auth modal and clicks 'Continue with Google' to complete Google SSO.
- Extracts __Secure-next-auth.session-token (including split/chunked tokens .0, .1).
- Validates the cookie header against OmniRoute (:20129) /api/providers/validate.
- Registers a new 'chatgpt-web' connection with 1-1 static proxy assignment.
- Appends the validated connection into 'chatgpt-web-pool' combo (Parity 100%).
"""

import json
import os
import re
import sys
import time
import requests
import sqlite3
import psutil
from playwright.sync_api import sync_playwright

OMNI_BASE = os.environ.get("OMNI_BASE_URL", "http://127.0.0.1:20129")
GPM_BASE = os.environ.get("GPM_API_BASE", "http://127.0.0.1:19995/api/v3")
WEB_POOL_ID = os.environ.get("WEB_POOL_ID", "9c68197d-410a-4267-a3e7-c843aa82cab0")
CODEX_POOL_ID = os.environ.get("CODEX_POOL_ID", "6a11df82-c1ba-4bb7-b8e7-5cda108ee11f")
GPM_DB_PATH = os.path.expandvars(r"%LOCALAPPDATA%\Programs\GPMLogin\profile\profile_data.db")

def extract_email(text: str) -> str:
    m = re.search(r"([a-zA-Z0-9_.+-]+@gmail\.com)", text or "")
    return m.group(1).lower() if m else (text or "").strip().lower()

def get_or_create_proxy(host: str, port: int, user: str = "", pwd: str = "") -> str | None:
    try:
        r_px = requests.get(f"{OMNI_BASE}/api/settings/proxies", timeout=10).json()
        for it in r_px.get("items", []):
            if it.get("host") == host and it.get("port") == port:
                return it["id"]
        r_cr = requests.post(f"{OMNI_BASE}/api/settings/proxies", json={
            "name": f"Proxy {host}:{port}",
            "type": "http",
            "host": host,
            "port": port,
            "username": user,
            "password": pwd
        }, timeout=10).json()
        return r_cr.get("id")
    except Exception as e:
        print(f"  [!] Lỗi resolve proxy: {e}")
        return None

def assign_proxy_to_conn(cid: str, proxy_id: str):
    if not proxy_id:
        return
    try:
        r = requests.put(
            f"{OMNI_BASE}/api/settings/proxies/assignments",
            json={"scope": "account", "scopeId": cid, "proxyId": proxy_id},
            timeout=10
        )
        print(f"  [✓] Gán Proxy ID {proxy_id} cho Connection {cid} (Status {r.status_code})")
    except Exception as e:
        print(f"  [!] Lỗi gán proxy: {e}")

def add_conn_to_web_combo(cid: str, email: str):
    try:
        combos = requests.get(f"{OMNI_BASE}/api/combos", timeout=10).json().get("combos", [])
        cb_list = [c for c in combos if c.get("id") == WEB_POOL_ID]
        if cb_list:
            cb = cb_list[0]
            cur = [m.get("connectionId") for m in cb.get("models", [])]
            if cid not in cur:
                short_user = email.split("@")[0]
                cb["models"].append({
                    "id": f"chatgpt-web-pool-model-{len(cur)+1}-{cid[:8]}",
                    "kind": "model",
                    "model": "chatgpt-web/gpt-5.6-sol-high",
                    "providerId": "chatgpt-web",
                    "connectionId": cid,
                    "weight": 0,
                    "label": f"sol-acc-{len(cur)+1}: {short_user}"
                })
                requests.put(f"{OMNI_BASE}/api/combos/{WEB_POOL_ID}", json=cb, timeout=10)
                print(f"  [+] Đã nạp vào chatgpt-web-pool -> Tổng models: {len(cb['models'])}")
    except Exception as e:
        print(f"  [!] Lỗi add web combo: {e}")

def sync_single_account(target: dict) -> bool:
    email = target["email"]
    pid = target["pid"]
    proxy_id = target.get("proxy_id")
    raw_proxy = target.get("raw_proxy")

    print("\n" + "="*70)
    print(f"[*] ĐỒNG BỘ SESSION WEB: {email} (PID: {pid})")
    print(f"[*] PROXY: {raw_proxy} (Proxy ID: {proxy_id})")
    print("="*70)

    # 1. Kiểm tra xem connection đã tồn tại chưa
    r_omni = requests.get(f"{OMNI_BASE}/api/providers", timeout=10).json()
    existing = [c for c in r_omni.get("connections", []) if c.get("provider") == "chatgpt-web" and email in (c.get("name") or "")]
    if existing:
        print(f"  [i] Tài khoản {email} đã có connection chatgpt-web ({existing[0]['id']})")
        return True

    # 2. Khởi động GPM Profile
    r_start = requests.get(f"{GPM_BASE}/profiles/start/{pid}?win_scale=0.8", timeout=25).json()
    if not r_start.get("success") or not r_start.get("data"):
        print(f"  [!] Không thể mở profile {pid}:", r_start)
        return False

    cdp = r_start["data"].get("remote_debugging_address")
    proc_id = r_start["data"].get("process_id")
    time.sleep(2.5)

    created_cid = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://{cdp}", timeout=20000)
            ctx = browser.contexts[0]
            pages = ctx.pages
            p = pages[0] if pages else ctx.new_page()

            p.goto("https://chatgpt.com/", timeout=45000)
            p.wait_for_timeout(3000)

            # Vượt rào static cookie banner bằng JS evaluation
            p.evaluate("""() => {
                const banner = document.querySelector("[data-octane-static-cookie-consent]");
                if (banner) banner.remove();
                const btn = document.querySelector("button[commandfor='mobile-auth-dialog']");
                if (btn) btn.click();
            }""")
            p.wait_for_timeout(1500)

            # Trigger Google SSO
            p.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll("button, a"));
                const g = btns.find(b => b.innerText && b.innerText.includes("Google"));
                if (g) g.click();
            }""")

            # Điều hướng qua các checkpoint account chooser / continue
            for step in range(12):
                p.wait_for_timeout(3000)
                u = p.url
                if "chatgpt.com" in u and "auth" not in u:
                    print("  [✓] Đã điều hướng vào trang chatgpt.com thành công!")
                    break
                if "accountchooser" in u or "chooseaccount" in u:
                    row = p.locator("[data-identifier], [data-email], li, div[role='link']").first
                    if row.count() > 0:
                        row.click(force=True)
                        p.wait_for_timeout(3000)
                        continue
                if "about-you" in u:
                    short = email.split('@')[0].capitalize()
                    ninp = p.locator("input[name='name']").first
                    if ninp.count() > 0 and not ninp.input_value(): ninp.fill(short)
                    ainp = p.locator("input[name='age']").first
                    if ainp.count() > 0 and not ainp.input_value(): ainp.fill("24")
                    sbtn = p.locator("button[type='submit']").first
                    if sbtn.count() > 0: sbtn.click(force=True)
                    p.wait_for_timeout(3000)
                    continue
                c_btn = p.locator("button:has-text('Tiếp tục'), button:has-text('Continue')").first
                if c_btn.count() > 0 and c_btn.is_visible():
                    c_btn.click(force=True)
                    p.wait_for_timeout(3000)
                    continue

            p.wait_for_timeout(3000)

            # Trích xuất cookies và validate
            cookies = ctx.cookies(["https://chatgpt.com"])
            cookie_parts = [f"{c['name']}={c['value']}" for c in cookies]
            full_cookie = "; ".join(cookie_parts)

            r_val = requests.post(f"{OMNI_BASE}/api/providers/validate", json={
                "provider": "chatgpt-web",
                "apiKey": full_cookie
            }, timeout=15).json()
            is_valid = r_val.get("valid") is True
            print(f"  [*] Kết quả kiểm tra Cookie OmniRoute: {is_valid}")

            if is_valid:
                r_cr = requests.post(f"{OMNI_BASE}/api/providers", json={
                    "provider": "chatgpt-web",
                    "name": f"{email} (GPM Web)",
                    "apiKey": full_cookie,
                    "isActive": True
                }, timeout=15).json()
                created_cid = r_cr.get("connection", {}).get("id") or r_cr.get("id")
                print(f"  [🎉] Tạo thành công Connection: {created_cid}")

                if created_cid and proxy_id:
                    assign_proxy_to_conn(created_cid, proxy_id)
                if created_cid:
                    add_conn_to_web_combo(created_cid, email)

            browser.close()
    except Exception as e:
        print(f"  [!] Exception trong phiên {email}: {e}")
    finally:
        # BẮT BUỘC: DUAL-STAGE TEARDOWN CHỐNG TREO MÁY
        try:
            requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
        except Exception:
            pass
        if proc_id:
            try:
                pr = psutil.Process(proc_id)
                for child in pr.children(recursive=True):
                    try: child.kill()
                    except Exception: pass
                pr.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    return bool(created_cid)

def discover_missing_web_accounts() -> list[dict]:
    # 1. Lấy danh sách kết nối Codex & Web hiện có
    r_omni = requests.get(f"{OMNI_BASE}/api/providers", timeout=10).json()
    conns = r_omni.get("connections", [])
    web_emails = set()
    codex_emails = set()
    for c in conns:
        em = extract_email((c.get("name") or "") + " " + (c.get("email") or ""))
        if not em: continue
        if c.get("provider") == "chatgpt-web":
            web_emails.add(em)
        elif c.get("provider") == "codex":
            codex_emails.add(em)

    missing = codex_emails - web_emails
    print(f"Tài khoản có trên Codex nhưng thiếu trên Web ({len(missing)}): {list(missing)}")
    if not missing:
        return []

    # 2. Quét SQLite GPMLogin lấy PID & Raw Proxy
    conn = sqlite3.connect(GPM_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT Id, Name, JsonData FROM Profiles")
    rows = cur.fetchall()
    conn.close()

    targets = []
    for pid, name, jdata in rows:
        em = extract_email(name)
        if em in missing:
            raw_proxy = None
            try: raw_proxy = json.loads(jdata).get("Proxy")
            except: pass

            proxy_id = None
            if raw_proxy:
                parts = raw_proxy.split(":")
                host = parts[0]
                port = int(parts[1])
                user = parts[2] if len(parts) > 2 else ""
                pwd = parts[3] if len(parts) > 3 else ""
                proxy_id = get_or_create_proxy(host, port, user, pwd)

            targets.append({
                "email": em,
                "pid": pid,
                "proxy_id": proxy_id,
                "raw_proxy": raw_proxy
            })
    return targets

def main():
    print("="*75)
    print("ĐỒNG BỘ TỰ ĐỘNG TÀI KHOẢN TỪ CODEX SANG CHATGPT-WEB-POOL")
    print("="*75)

    targets = discover_missing_web_accounts()
    if not targets:
        print("Tất cả tài khoản Codex đã có mặt trên Web Pool. Parity 100%!")
        return

    success_cnt = 0
    for t in targets:
        ok = sync_single_account(t)
        if ok: success_cnt += 1
        print(f"KẾT QUẢ CHO {t['email']}: {'THÀNH CÔNG' if ok else 'THẤT BẠI'}")
        print("  [*] Nghỉ 5s an toàn trước profile tiếp theo...")
        time.sleep(5)

    print("\n" + "="*75)
    print(f"HOÀN TẤT ĐỒNG BỘ: {success_cnt}/{len(targets)} TÀI KHOẢN THÀNH CÔNG!")
    print("="*75)

if __name__ == "__main__":
    main()
