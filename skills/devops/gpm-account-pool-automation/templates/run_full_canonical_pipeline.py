"""
Canonical Full Pipeline Template: GPM Login + S7 Device Bypass + 2FA Authenticator Setup + Hot-Session OAuth Antigravity
========================================================================================================================
Quy trình chuẩn 4 bước khép kín cho Farm Kibe theo chỉ đạo 2026-09-08:
1. Login Google: mở Chromium qua proxy 1:1, giải Audio reCAPTCHA, duyệt S7 Google Prompt / Security Code 10 số.
2. 2FA Setup: nếu chưa có, vào /two-step-verification/authenticator, bốc Base32 Secret Key, tính True UTC TOTP xác nhận, lưu Dual Excel.
3. Hot-Session OAuth: giữ nguyên tab nóng, vào link authorize OmniRoute (timeout 120s), cấp quyền Antigravity, exchange token, gán proxy 1:1, sync models.
4. Combo & Proof: append vào combo ag-gemini-pool-3, chụp ảnh màn hình Samsung S7 bằng chứng qua ADB screencap.
"""

import os
import sys
import time
import re
import json
import logging
import subprocess
import urllib.parse
import urllib.request
import email.utils
import openpyxl
import pyotp
import requests
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CanonicalPipeline")

ADB_EXE = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
GPM_PROFILE_BASE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"
MASTER_EXCEL = r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx"
CLEAN_V2_EXCEL = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
OMNI_BASE = "http://127.0.0.1:20129"
STATUS_JSON = r"D:\Taadaa\GPM auto\config\oauth_pipeline_status.json"

sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
try:
    from append_to_combo_pool3 import append_connections
    from run_oauth_s7_pipeline import solve_recaptcha_audio, get_s7_security_code, approve_s7_google_prompt
except ImportError:
    append_connections = None
    solve_recaptcha_audio = None
    get_s7_security_code = None
    approve_s7_google_prompt = None


def get_google_server_utc_time() -> float:
    try:
        req = urllib.request.Request("https://www.google.com", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            date_str = resp.headers.get("Date")
            if date_str:
                return time.mktime(email.utils.parsedate(date_str))
    except Exception:
        pass
    return time.time()


def sync_secret_to_excels(target_email: str, secret_key: str):
    """Lưu đồng bộ Secret Key 2FA vào cả 2 file Excel."""
    try:
        if os.path.exists(MASTER_EXCEL):
            wb = openpyxl.load_workbook(MASTER_EXCEL)
            for sheet_name in ["Kibe_Farm_S7", "Sheet1"]:
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    for r in range(2, ws.max_row + 1):
                        em = str(ws.cell(r, 2).value or "").strip().lower()
                        if target_email.lower() == em:
                            ws.cell(r, 4, secret_key)
            wb.save(MASTER_EXCEL)

        if os.path.exists(CLEAN_V2_EXCEL):
            wb_clean = openpyxl.load_workbook(CLEAN_V2_EXCEL)
            ws_clean = wb_clean.active
            for r in range(2, ws_clean.max_row + 1):
                em = str(ws_clean.cell(r, 2).value or "").strip().lower()
                if target_email.lower() == em:
                    ws_clean.cell(r, 4, secret_key)
            wb_clean.save(CLEAN_V2_EXCEL)
        logger.info(f"✅ [SAVE 2FA OK] {target_email} -> {secret_key}")
    except Exception as e:
        logger.error(f"❌ [SAVE 2FA ERROR] {target_email}: {e}")


def process_canonical_account(acc: dict) -> dict:
    """Xử lý trọn gói 1 tài khoản theo Canonical Full Pipeline."""
    mid = acc["mid"]
    email = acc["email"]
    password = acc["password"]
    port = acc["port"]
    serial = acc["serial"]
    prof_dir = acc["profile_dir"]
    totp_secret = acc.get("totp_secret", "")

    singbox_port = 20000 + (port - 5100) if 5000 < port < 6000 else 20000 + mid
    proxy_url = f"http://192.168.110.2:{singbox_port}"

    logger.info(f"\n{'='*60}")
    logger.info(f"[CANONICAL PIPELINE] M{mid:02d} | {email} | Port {port} -> Singbox {singbox_port}")
    logger.info(f"{'='*60}")

    captured_code = None

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=prof_dir,
                executable_path=CHROME_EXE,
                proxy={"server": proxy_url},
                locale="vi-VN",
                headless=False,
                args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled", "--lang=vi-VN,vi"]
            )
        except Exception as e:
            logger.error(f"Lỗi launch Chrome M{mid:02d}: {e}")
            return {"status": "LAUNCH_FAILED", "email": email}

        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(35000)

            # ----------------------------------------------------
            # BƯỚC 1: ĐĂNG NHẬP GOOGLE & VƯỢT BẢO MẬT S7
            # ----------------------------------------------------
            page.goto("https://accounts.google.com/ServiceLogin", wait_until="domcontentloaded", timeout=40000)
            time.sleep(3)

            em_inp = page.locator('input[type="email"], input#identifierId').first
            if em_inp.count() > 0 and em_inp.is_visible():
                em_inp.fill(email)
                page.keyboard.press("Enter")
                time.sleep(3)

            if solve_recaptcha_audio:
                solve_recaptcha_audio(page)

            pw_inp = page.locator('input[type="password"], input[name="Passwd"]').first
            if pw_inp.count() > 0 and pw_inp.is_visible():
                pw_inp.fill(password)
                page.keyboard.press("Enter")
                time.sleep(4)

            # Loop giải quyết thách thức bảo mật S7
            for _ in range(18):
                cur_url = page.url.lower()
                body_txt = page.inner_text("body").lower() if page.locator("body").count() > 0 else ""

                if "myaccount.google.com" in cur_url and "signin" not in cur_url:
                    logger.info(f"[M{mid:02d}] Đã vào trang MyAccount thành công.")
                    break

                # 1. Google Prompt (challenge/dp)
                if ("challenge/dp" in cur_url or "nhấn vào có" in body_txt or "kiểm tra điện thoại" in body_txt) and approve_s7_google_prompt:
                    m_pin = re.search(r'(?:nhấn vào|chọn|tap|số|number)\s*(\d{1,2})', body_txt, re.I)
                    target_pin = int(m_pin.group(1)) if m_pin else None
                    logger.info(f"[M{mid:02d}] Phát hiện Google Prompt (PIN {target_pin}), duyệt trên S7 {serial}...")
                    approve_s7_google_prompt(mid, serial, target_pin, target_email=email)
                    time.sleep(5)
                    continue

                # 2. Security Code 10 số (challenge/ootp)
                if ("challenge/ootp" in cur_url or "mã bảo mật" in body_txt) and get_s7_security_code:
                    code_inp = page.locator('input[name="Pin"], input#security-code-input').first
                    if code_inp.count() > 0 and code_inp.is_visible():
                        sec_code = get_s7_security_code(mid, serial, email)
                        if sec_code:
                            code_inp.fill(sec_code)
                            page.keyboard.press("Enter")
                            time.sleep(5)
                            continue

                # 3. TOTP nếu đã có secret
                if totp_secret and ("totp" in cur_url or page.locator('input#totpPin').count() > 0):
                    totp_inp = page.locator('input#totpPin, input[name="totpPin"]').first
                    if totp_inp.count() > 0 and totp_inp.is_visible():
                        t_code = pyotp.TOTP(totp_secret.replace(" ", "").upper()).at(get_google_server_utc_time())
                        totp_inp.fill(t_code)
                        page.keyboard.press("Enter")
                        time.sleep(5)
                        continue

                # Dismiss Onboarding / Bỏ qua
                dismiss_btn = page.locator('button:has-text("Bỏ qua"), button:has-text("Để sau"), button:has-text("Not now"), button:has-text("Huỷ")').first
                if dismiss_btn.count() > 0 and dismiss_btn.is_visible():
                    dismiss_btn.click()
                    time.sleep(2)
                    continue

                time.sleep(2)

            # ----------------------------------------------------
            # BƯỚC 2: KIỂM TRA & BẬT 2FA GOOGLE AUTHENTICATOR
            # ----------------------------------------------------
            if not totp_secret:
                logger.info(f"[M{mid:02d}] Chưa có 2FA, điều hướng tới /two-step-verification/authenticator...")
                page.goto("https://myaccount.google.com/two-step-verification/authenticator", wait_until="domcontentloaded", timeout=40000)
                time.sleep(3)

                # Loop đợi re-auth password nếu có
                for _ in range(5):
                    pw_re = page.locator('input[type="password"]').first
                    if pw_re.count() > 0 and pw_re.is_visible():
                        pw_re.fill(password)
                        page.keyboard.press("Enter")
                        time.sleep(4)
                    if "challenge" not in page.url.lower():
                        break
                    time.sleep(2)

                page_content = page.inner_text("body").lower() if page.locator("body").count() > 0 else ""
                setup_btn = page.locator('button:has-text("Thiết lập"), button:has-text("Set up")').first

                if setup_btn.count() > 0 and setup_btn.is_visible():
                    logger.info(f"[M{mid:02d}] Bấm nút Thiết lập Authenticator...")
                    setup_btn.click(force=True)
                    time.sleep(2.5)

                    cant_scan = page.locator('div[role="dialog"] button:has-text("quét"), div[role="dialog"] button:has-text("scan"), a:has-text("quét")').first
                    if cant_scan.count() > 0 and cant_scan.is_visible():
                        cant_scan.click(force=True)
                        time.sleep(2)

                    dialog = page.locator('div[role="dialog"]')
                    dialog_text = dialog.inner_text() if dialog.count() > 0 else page.inner_text("body")
                    key_match = re.search(r'\b([a-z2-7\s]{26,40})\b', dialog_text, re.I)
                    if key_match:
                        raw_key = key_match.group(1).replace(" ", "").strip().upper()
                        if len(raw_key) == 32:
                            logger.info(f"[M{mid:02d}] 🔑 Bốc được Base32 Secret Key: {raw_key}")
                            next_btn = page.locator('div[role="dialog"] button:has-text("Tiếp theo"), div[role="dialog"] button:has-text("Next")').first
                            if next_btn.count() > 0:
                                next_btn.click()
                                time.sleep(2)

                            totp_val = pyotp.TOTP(raw_key).at(get_google_server_utc_time())
                            inp_code = page.locator('div[role="dialog"] input[type="tel"], div[role="dialog"] input[type="text"]').first
                            if inp_code.count() > 0 and inp_code.is_visible():
                                inp_code.fill(totp_val)
                                verify_btn = page.locator('div[role="dialog"] button:has-text("Xác minh"), div[role="dialog"] button:has-text("Verify")').first
                                if verify_btn.count() > 0:
                                    verify_btn.click()
                                    time.sleep(3)
                            sync_secret_to_excels(email, raw_key)
                            totp_secret = raw_key
                            logger.info(f"✅ [M{mid:02d}] Kích hoạt 2FA Authenticator thành công!")
                elif any(w in page_content for w in ["đổi ứng dụng xác thực", "change authenticator"]):
                    logger.info(f"[M{mid:02d}] 2FA Authenticator đã được kích hoạt trước đó.")

            # ----------------------------------------------------
            # BƯỚC 3: HOT-SESSION OAUTH VÀO OMNIROUTE (TIMEOUT >= 120S)
            # ----------------------------------------------------
            logger.info(f"[M{mid:02d}] Giữ hot session, lấy authorize URL từ OmniRoute...")
            redirect_uri = f"{OMNI_BASE}/callback"
            r_auth = requests.get(f"{OMNI_BASE}/api/oauth/antigravity/authorize?redirect_uri={urllib.parse.quote(redirect_uri, safe='')}", timeout=10).json()
            auth_url = r_auth["authUrl"]
            state = r_auth.get("state", "")
            code_verifier = r_auth.get("codeVerifier", "")

            def on_request(req):
                nonlocal captured_code
                if "/callback" in req.url and "code=" in req.url:
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
                    if "code" in qs and qs["code"]:
                        captured_code = qs["code"][0]
                        logger.info(f"[M{mid:02d}] 🎉 Bắt được Authorization Code: {captured_code[:15]}...")

            page.on("request", on_request)
            page.goto(auth_url, timeout=40000)
            time.sleep(3)

            start_oauth_t = time.time()
            account_picked = False

            while time.time() - start_oauth_t < 120:  # TIMEOUT >= 120s BẮT BUỘC
                if captured_code:
                    break

                # 1. Account Chooser
                if not account_picked:
                    acc_elem = page.locator(f'div[data-identifier="{email}"], div:has-text("{email}")').first
                    if acc_elem.count() > 0 and acc_elem.is_visible():
                        logger.info(f"[M{mid:02d}] Chọn tài khoản: {email}")
                        acc_elem.click()
                        account_picked = True
                        time.sleep(3)
                        continue

                # 2. Consent Button (Cho phép / Continue / Allow)
                for btn_txt in ["Cho phép", "Allow", "Tiếp tục", "Continue", "#submit_approve_access"]:
                    c_btn = page.locator(f'button:has-text("{btn_txt}"), div[role="button"]:has-text("{btn_txt}")').first
                    if c_btn.count() > 0 and c_btn.is_visible():
                        logger.info(f"[M{mid:02d}] Bấm nút consent: {btn_txt}")
                        c_btn.click()
                        time.sleep(3)
                        break

                time.sleep(1.5)

            if not captured_code:
                logger.error(f"[M{mid:02d}] ❌ Timeout 120s không bắt được callback code.")
                return {"status": "OAUTH_TIMEOUT", "email": email}

            # Exchange Token
            logger.info(f"[M{mid:02d}] Gửi exchange code lên OmniRoute...")
            ex_resp = requests.post(f"{OMNI_BASE}/api/oauth/antigravity/exchange", json={
                "code": captured_code,
                "redirectUri": redirect_uri,
                "codeVerifier": code_verifier,
                "state": state
            }, timeout=20)

            if ex_resp.status_code != 200:
                logger.error(f"[M{mid:02d}] Exchange thất bại HTTP {ex_resp.status_code}: {ex_resp.text}")
                return {"status": "EXCHANGE_FAILED", "email": email}

            conn_data = ex_resp.json().get("connection", {})
            cid = conn_data.get("id")
            logger.info(f"[M{mid:02d}] ✅ OAuth thành công! Connection ID: {cid}")

            # Gán Proxy 1:1
            try:
                p_items = requests.get(f"{OMNI_BASE}/api/settings/proxies", timeout=5).json().get("items", [])
                for px in p_items:
                    if px.get("port") == port:
                        requests.put(f"{OMNI_BASE}/api/settings/proxies/assignments", json={
                            "scope": "account", "scopeId": cid, "proxyId": px["id"]
                        }, timeout=5)
                        logger.info(f"[M{mid:02d}] ✅ Gán Proxy ID {px['id']} (Port {port})")
                        break
            except Exception as pe:
                logger.warning(f"[M{mid:02d}] Lỗi gán proxy: {pe}")

            # Sync Models
            try:
                requests.post(f"{OMNI_BASE}/api/providers/{cid}/sync-models", timeout=10)
                logger.info(f"[M{mid:02d}] ✅ Sync-models OK")
            except Exception as se:
                logger.warning(f"[M{mid:02d}] Lỗi sync-models: {se}")

            # Chụp ảnh màn hình Samsung S7 bằng chứng vật lý qua ADB
            s7_proof_path = rf"C:\Users\Kibe\AppData\Local\hermes\cache\m{mid:02d}_s7_canonical_proof.png"
            try:
                subprocess.run([ADB_EXE, "-s", serial, "exec-out", "screencap", "-p"], stdout=open(s7_proof_path, "wb"), timeout=10)
                logger.info(f"[M{mid:02d}] 📸 Đã lưu ảnh S7 proof: {s7_proof_path}")
            except Exception as ae:
                logger.warning(f"[M{mid:02d}] Không thể chụp S7 proof: {ae}")

            return {
                "status": "SUCCESS",
                "mid": mid,
                "email": email,
                "port": port,
                "cid": cid,
                "secret_key": totp_secret,
                "proof_path": s7_proof_path
            }

        finally:
            ctx.close()
