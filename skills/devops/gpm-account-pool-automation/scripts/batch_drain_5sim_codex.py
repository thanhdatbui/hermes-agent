#!/usr/bin/env python3
"""
Batch Drain 5sim Codex OAuth Runner for GPMLogin Profiles.
- Filters candidate profiles by OpenAI/ChatGPT cookies (O(1) SQLite scan).
- Snipes only physical mobile Smart TNT prefixes (970, 930, 907, 919, 920, 928, 929).
- Instantly cancels rejected/timeout orders for 100% refund.
- Binds completed Codex connections directly into OmniRoute 'codex-terra-pool'.
"""

import json
import os
import re
import sqlite3
import sys
import time
import requests
import psutil
from playwright.sync_api import sync_playwright

TOKEN_FILE = r"C:\Users\Kibe\.5sim_token"
if not os.path.exists(TOKEN_FILE):
    print(f"Error: {TOKEN_FILE} not found.")
    sys.exit(1)

with open(TOKEN_FILE, "r") as f:
    TOKEN = f.read().strip()

H_5SIM = {"Authorization": "Bearer " + TOKEN, "Accept": "application/json"}
OMNI_BASE = "http://127.0.0.1:20129"
GPM_BASE = "http://127.0.0.1:19995/api/v3"
TERRA_POOL_ID = "6a11df82-c1ba-4bb7-b8e7-5cda108ee11f"
LUNA_POOL_ID = "f01e7657-f739-418a-8ba0-009a9923d8fb"
TERRA_SHORT_ID = "54e4869e-64b9-400f-a463-aab431dafcf2"
LUNA_SHORT_ID = "2d34cbef-3436-409d-b69a-26d2a89e0571"
BASE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"

SMART_PREFIXES = ("930", "970", "907", "919", "920", "928", "929")

def get_5sim_balance():
    try:
        r = requests.get("https://5sim.net/v1/user/profile", headers=H_5SIM, timeout=10)
        return float(r.json().get("balance", 0.0))
    except Exception as e:
        print("[!] Lỗi 5sim profile:", e)
        return 0.0

def cancel_5sim(oid):
    try:
        requests.get(f"https://5sim.net/v1/user/cancel/{oid}", headers=H_5SIM, timeout=10)
    except Exception:
        pass

def finish_5sim(oid):
    try:
        requests.get(f"https://5sim.net/v1/user/finish/{oid}", headers=H_5SIM, timeout=10)
    except Exception:
        pass

def clean_active_orders():
    try:
        orders = requests.get("https://5sim.net/v1/user/orders?category=activation", headers=H_5SIM, timeout=10).json()
        active = [o for o in orders.get("Data", []) if o.get("status") in ["PENDING", "RECEIVED"]]
        for o in active:
            cancel_5sim(o.get("id"))
    except Exception:
        pass

def snipe_smart_sim():
    for _ in range(40):
        try:
            r = requests.get("https://5sim.net/v1/user/buy/activation/philippines/virtual58/openai", headers=H_5SIM, timeout=10)
            if r.status_code == 200 and "no free phones" not in r.text:
                d = r.json()
                oid = d.get("id")
                phone = d.get("phone", "")
                pref = phone[3:6]
                if pref in SMART_PREFIXES:
                    print(f"  [🔥 SỐ SMART BẮT ĐƯỢC] {phone} (Đầu {pref}, Order {oid})!")
                    return d
                else:
                    cancel_5sim(oid)
        except Exception:
            pass
        time.sleep(0.3)
    return None

def add_connection_to_combo(conn_id, email=""):
    try:
        combos = requests.get(f"{OMNI_BASE}/api/combos", timeout=10).json().get("combos", [])
        for cb_name, model_name, pfx in [
            ("codex-terra-pool", "codex/gpt-5.6-terra", "codex-terra-pool-model"),
            ("codex-luna-pool", "codex/gpt-5.6-luna-medium", "codex-luna-model"),
            ("codex-terra", "codex/gpt-5.6-terra", "codex-terra-short-model"),
            ("codex-luna", "codex/gpt-5.6-luna-medium", "codex-luna-short-model"),
        ]:
            cb_list = [c for c in combos if c.get("name") == cb_name]
            if cb_list:
                cb = cb_list[0]
                cur = [m.get("connectionId") for m in cb.get("models", [])]
                if conn_id not in cur:
                    cb["models"].append({
                        "id": f"{pfx}-{len(cur)+1}-{conn_id[:8]}",
                        "kind": "model",
                        "model": model_name,
                        "providerId": "codex",
                        "connectionId": conn_id,
                        "weight": 1 if "terra" in pfx else 0,
                        "label": f"codex-{len(cur)+1}: {email}"
                    })
                    requests.put(f"{OMNI_BASE}/api/combos/{cb['id']}", json=cb, timeout=10)
        print(f"  [+] Đã cập nhật 4 Combos Codex cho {conn_id} ({email})!")
    except Exception as e:
        print("  [!] Lỗi add combo:", e)

def stop_gpm(pid, proc_id=None):
    try:
        requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
    except Exception:
        pass
    if proc_id:
        try:
            proc = psutil.Process(proc_id)
            for child in proc.children(recursive=True):
                try: child.kill()
                except Exception: pass
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def discover_candidate_profiles():
    # 1. Lấy danh sách kết nối Codex hiện có trong OmniRoute
    r_c = requests.get(f"{OMNI_BASE}/api/providers", timeout=10).json()
    active_emails = set()
    for c in r_c.get("connections", []):
        if c.get("provider") == "codex":
            m = re.search(r"([a-zA-Z0-9_.+-]+@gmail\.com)", (c.get("name") or "") + " " + (c.get("email") or ""))
            if m:
                active_emails.add(m.group(1).lower())

    # 2. Quét SQLite profile_data.db trong GPMLogin
    db_path = os.path.join(BASE_DIR, "profile_data.db")
    if not os.path.exists(db_path):
        print(f"[!] Không tìm thấy DB GPM tại {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT Id, Name, ProfilePath FROM Profiles")
    rows = cur.fetchall()
    conn.close()

    candidates = []
    for pid, name, p_path in rows:
        if not p_path:
            continue
        m = re.search(r"([a-zA-Z0-9_.+-]+@gmail\.com)", name or "")
        if not m:
            continue
        email = m.group(1).lower()
        if email in active_emails:
            continue

        cookie_db = os.path.join(BASE_DIR, p_path, "Default", "Network", "Cookies")
        if not os.path.exists(cookie_db):
            continue

        try:
            c = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
            cr = c.cursor()
            cr.execute("SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%openai%' OR host_key LIKE '%chatgpt%'")
            cnt = cr.fetchone()[0]
            c.close()
            if cnt > 0:
                candidates.append({"id": pid, "email": email, "name": name, "cookie_count": cnt})
        except Exception:
            pass

    # Ưu tiên các profile có session cookie sâu nhất
    candidates.sort(key=lambda x: -x["cookie_count"])
    return candidates

def verify_single_profile(profile, pw):
    pid = profile["id"]
    email = profile["email"]

    print("\n" + "="*70)
    print(f"[*] BẮT ĐẦU XÁC THỰC PROFILE: {email} (ID: {pid})")
    print("="*70)

    r_start = requests.get(f"{GPM_BASE}/profiles/start/{pid}?win_scale=0.8", timeout=20).json()
    if not r_start.get("success") or not r_start.get("data"):
        print(f"  [!] Không thể khởi động profile GPM: {r_start.get('message')}")
        return False
    cdp = r_start["data"].get("remote_debugging_address")
    proc_id = r_start["data"].get("process_id")
    time.sleep(2.5)

    browser = None
    verified = False
    try:
        browser = pw.chromium.connect_over_cdp(f"http://{cdp}", timeout=15000)
        context = browser.contexts[0]
        pages = [pg for pg in context.pages if not pg.url.startswith("chrome-extension://")]
        page = pages[0] if pages else context.new_page()

        # Forward callback về 127.0.0.1
        def on_req(req):
            url = req.url
            if "1455" in url and ("callback" in url or "code=" in url):
                try:
                    local_url = url.replace("localhost", "127.0.0.1")
                    requests.get(local_url, timeout=5)
                except Exception:
                    pass
        page.on("request", on_req)

        for cycle in range(1, 6):
            bal_now = get_5sim_balance()
            if bal_now < 0.1077:
                print(f"  [!] Hết tiền 5sim (${bal_now:.4f}), dừng chu kỳ!")
                break

            print(f"\n--- [CHU KỲ {cycle}/5] Mở Auth Flow tươi mới từ OmniRoute ---")
            cb = requests.get(f"{OMNI_BASE}/api/oauth/codex/start-callback-server", timeout=10).json()
            auth_url = cb.get("authUrl")
            page.goto(auth_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(3)

            for _ in range(5):
                cur_url = page.url
                cur_title = page.title()

                if "Authentication Successful" in cur_title or ("1455" in cur_url and "callback" in cur_url):
                    break
                if "add-phone" in cur_url:
                    break

                if "log-in" in cur_url:
                    btn_g = page.locator("button:has-text('Continue with Google'), button:has-text('Tiếp tục với Google')").first
                    if btn_g.count() > 0:
                        btn_g.click(force=True)
                        time.sleep(3.5)
                        continue

                if "choose-an-account" in cur_url or "accountchooser" in cur_url:
                    row = page.locator("button, li, div[role='button']").first
                    if row.count() > 0:
                        row.click(force=True)
                        time.sleep(3)
                        continue

                if "accounts.google.com" in cur_url:
                    btn_c = page.locator("button:has-text('Continue'), button:has-text('Tiếp tục')").first
                    if btn_c.count() > 0:
                        btn_c.click(force=True)
                        time.sleep(3)
                        continue

                btn_auth = page.locator("button:has-text('Authorize'), button:has-text('Continue'), button:has-text('Tiếp tục')").first
                if btn_auth.count() > 0:
                    btn_auth.click(force=True)
                    time.sleep(3)

                time.sleep(1)

            if "add-phone" in page.url:
                try:
                    page.locator("select").first.select_option(value="PH")
                    page.wait_for_timeout(300)
                except Exception:
                    pass

                order = snipe_smart_sim()
                if not order:
                    continue

                oid = order.get("id")
                phone = order.get("phone")
                digits = phone.lstrip("+")
                local = digits[2:] if digits.startswith("63") else digits

                print(f"  [>] Thử số Smart: {phone} (Local: {local}, Order: {oid})")
                try:
                    tel = page.locator("input[type='tel']").first
                    tel.fill("")
                    tel.fill(local)
                    page.wait_for_timeout(300)

                    page.locator("button[type='submit']").first.click(force=True)
                    page.wait_for_timeout(3500)

                    if "phone-verification" in page.url:
                        print(f"  [🔥🔥🔥] OpenAI chấp nhận số! Chờ OTP...")
                        otp_code = None
                        for sec in range(1, 6):
                            time.sleep(8)
                            chk = requests.get(f"https://5sim.net/v1/user/check/{oid}", headers=H_5SIM).json()
                            sms_arr = chk.get("sms") or []
                            print(f"    [{sec*8}s] SMS count: {len(sms_arr)}")
                            if sms_arr:
                                otp_code = sms_arr[0].get("code")
                                print(f"    [🎉🎉🎉] OTP NHẬN ĐƯỢC: {otp_code}!")
                                break

                        if not otp_code:
                            resend_btn = page.locator("button:has-text('Resend text message'), button:has-text('Gửi lại tin nhắn văn bản')").first
                            if resend_btn.count() > 0:
                                resend_btn.click(force=True)
                                page.wait_for_timeout(2000)
                                for sec in range(1, 6):
                                    time.sleep(8)
                                    chk = requests.get(f"https://5sim.net/v1/user/check/{oid}", headers=H_5SIM).json()
                                    sms_arr = chk.get("sms") or []
                                    if sms_arr:
                                        otp_code = sms_arr[0].get("code")
                                        break

                        if otp_code:
                            otp_in = page.locator("input[type='text'], input[name='code'], input[autocomplete='one-time-code']").first
                            otp_in.fill(otp_code)
                            page.wait_for_timeout(300)
                            page.locator("button[type='submit']").first.click(force=True)
                            page.wait_for_timeout(4000)

                            if "about-you" in page.url:
                                age_in = page.locator("input[type='number'], input[name='age']").first
                                if age_in.count() > 0:
                                    age_in.fill("27")
                                page.locator("button:has-text('Continue'), button:has-text('Tiếp tục')").first.click(force=True)
                                page.wait_for_timeout(4000)

                            finish_5sim(oid)
                            verified = True
                            break
                        else:
                            cancel_5sim(oid)
                    else:
                        cancel_5sim(oid)

                except Exception as e:
                    print("  [!] Lỗi thao tác form:", e)
                    cancel_5sim(oid)

            btn_ws = page.locator("button:has-text('Continue'), button:has-text('Tiếp tục')").first
            if btn_ws.count() > 0 and "consent" in page.url:
                btn_ws.click(force=True)
                time.sleep(4)

            poll = requests.post(f"{OMNI_BASE}/api/oauth/codex/poll-callback", json={}, timeout=10).json()
            if poll.get("success"):
                conn_id = poll.get("connection", {}).get("id")
                print(f"\n[🎉 THÀNH CÔNG] Đã thêm Connection: {conn_id} ({email})")
                add_connection_to_combo(conn_id)
                verified = True
                break

        browser.close()
    except Exception as e:
        print(f"  [!] Lỗi profile {email}: {e}")
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    stop_gpm(pid, proc_id)
    clean_active_orders()
    return verified

def main():
    print("="*75)
    print("CHẠY BATCH LIÊN TỤC VER TỪNG TÀI KHOẢN CHO ĐẾN KHI HẾT TIỀN 5SIM")
    print("="*75)

    clean_active_orders()
    candidates = discover_candidate_profiles()
    print(f"Tổng số profiles hợp lệ chờ xác thực: {len(candidates)}")

    success_accounts = []
    with sync_playwright() as pw:
        for idx, p in enumerate(candidates, 1):
            bal = get_5sim_balance()
            print(f"\n>>> [TIẾN ĐỘ #{idx}/{len(candidates)}] {p['email']} | Số dư 5sim: ${bal:.4f} <<<")
            if bal < 0.1077:
                print("\n[🎯 HOÀN TẤT] Số dư 5sim không còn đủ mua SIM Smart ($0.1077). Dừng tiến trình!")
                break

            ok = verify_single_profile(p, pw)
            if ok:
                success_accounts.append(p["email"])
                print(f"==> VER THÀNH CÔNG: {p['email']} (Tổng mới: {len(success_accounts)})")
                time.sleep(3)
            else:
                time.sleep(2)

    final_bal = get_5sim_balance()
    print("\n" + "="*75)
    print("TỔNG KẾT TOÀN BỘ TIẾN TRÌNH DRAIN 5SIM:")
    print(f"- Tổng số tài khoản Codex ver thành công mới: {len(success_accounts)}")
    print(f"- Danh sách tài khoản mới: {success_accounts}")
    print(f"- Số dư 5sim cuối cùng: ${final_bal:.4f}")
    print("="*75)

if __name__ == "__main__":
    main()
