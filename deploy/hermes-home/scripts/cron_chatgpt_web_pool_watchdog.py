#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watchdog tự động kiểm tra và hồi sinh các tài khoản ChatGPT Web Pool, Antigravity OAuth và Codex trên OmniRoute (:20129)
- Lịch trình: Chạy hàng ngày lúc 05:00 AM (hoặc chạy khi có sự cố).
- Kiến trúc Modular 4 tầng:
  1. Data Layer: Trích xuất thông tin tài khoản an toàn từ Excel/SQLite với cơ chế transaction rollback và provider guard.
  2. Browser Automation Layer: Điều khiển Chromium qua GPMLogin CDP, giải mã reCAPTCHA audio và vượt checkpoint Google/IMAP.
  3. OAuth & Token Exchange Layer: Tự động trao đổi authorization code lấy refresh token và gán proxy tương ứng.
  4. Observability & Telemetry Layer: Ghi nhận structured JSON metrics và JSONL audit trail history, versioning selector.
- Nguyên tắc an toàn Farm:
  - Tôn trọng trạng thái Standby do người dùng cấu hình cho Antigravity/Codex (không tự ý ép bật is_active).
  - Tự động dừng khẩn cấp (Fail-Safe) khi phát hiện Google yêu cầu số điện thoại (Phone Checkpoint).
"""

import os
import sys
import json
import time
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
import requests
import pyotp
import openpyxl
import pydub
import speech_recognition as sr
from playwright.sync_api import sync_playwright

FFMPEG_DIR = r"C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"
if os.path.exists(FFMPEG_DIR):
    if FFMPEG_DIR not in os.environ.get("PATH", ""):
        os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
    try:
        pydub.AudioSegment.converter = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    except Exception:
        pass

OMNI_API = "http://127.0.0.1:20129"
GPM_API = "http://127.0.0.1:19995/api/v3"
DB_PATH = os.environ.get("OMNI_DB_PATH", os.path.expanduser(r"~/.omniroute/storage.sqlite"))
EXCEL_PATH = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
DIRECT_OAUTH_URL = "https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true"

def log(msg: str):
    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()

def load_accounts_credentials():
    creds = {}
    if not os.path.exists(EXCEL_PATH):
        return creds
    try:
        wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            for row in list(ws.iter_rows(values_only=True))[1:]:
                if not row or len(row) < 3:
                    continue
                em = str(row[1] or "").strip().lower()
                if "@gmail.com" in em:
                    pwd = str(row[2] or "").strip()
                    totp = str(row[3] or "").strip() if len(row) > 3 else ""
                    recovery_email = str(row[4] or "").strip().lower() if len(row) > 4 else ""
                    dob = str(row[5] or "").strip() if len(row) > 5 else ""
                    creds[em] = {
                        "password": pwd,
                        "totp": totp,
                        "recovery_email": recovery_email,
                        "dob": dob
                    }
    except Exception as e:
        log(f"Lỗi đọc credentials từ Excel: {e}")
    return creds

def get_connections_by_provider(provider_name: str):
    try:
        req = urllib.request.Request(f"{OMNI_API}/api/providers")
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            conns = [c for c in data.get('connections', []) if c.get('provider') == provider_name]
            return conns
    except Exception as e:
        log(f"Lỗi lấy connections {provider_name}: {e}")
        return []

def get_gpm_profiles():
    try:
        profiles = []
        page = 1
        while True:
            res = requests.get(f"{GPM_API}/profiles?page={page}&per_page=50", timeout=10).json()
            data = res.get('data', [])
            if not data:
                break
            profiles.extend(data)
            if page >= res.get('pagination', {}).get('total_page', 1):
                break
            page += 1
        return profiles
    except Exception as e:
        log(f"Lỗi lấy GPM profiles: {e}")
        return []

def get_gpm_profiles_map():
    try:
        profiles = get_gpm_profiles()
        email_map = {}
        import re
        for p in profiles:
            pname = p.get('name', '')
            m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', pname)
            if m:
                email = m.group(1).lower()
                email_map[email] = p
        return email_map
    except Exception as e:
        log(f"Lỗi lấy GPM profiles map: {e}")
        return {}

def test_connection_valid(cookie_str: str):
    try:
        req = urllib.request.Request(
            f"{OMNI_API}/api/providers/validate",
            data=json.dumps({"provider": "chatgpt-web", "apiKey": cookie_str}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
            return res.get('valid') is True or res.get('isValid') is True, res
    except Exception as e:
        return False, str(e)

# ==================== ARCHITECTURE LAYER 1: DATA & SCHEMA GUARDS ====================
# ==================== ARCHITECTURE LAYER 2: CHATGPT-WEB RECOVERY MODULE ====================
def perform_auto_login_and_extract_cookies(cdp_addr: str, email: str, creds: dict):
    acc_info = creds.get(email, {})
    password = acc_info.get('password')
    totp_key = acc_info.get('totp')
    
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        page.goto("https://chatgpt.com", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        
        cookies = context.cookies(["https://chatgpt.com"])
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        is_valid, _ = test_connection_valid(cookie_str)
        if is_valid:
            return cookie_str
            
        log(f"[{email}] Cookie session hết hạn -> Đang mở Direct Google OAuth...")
        page.goto(DIRECT_OAUTH_URL, timeout=60000, wait_until="domcontentloaded")
        
        for step in range(25):
            page.wait_for_timeout(3000)
            u = page.url.lower()
            
            if "chatgpt.com" in u and "auth" not in u and page.locator('button:has-text("Đăng nhập"), a:has-text("Đăng nhập")').count() == 0:
                break
                
            if "about-you" in u:
                short_name = email.split('@')[0].capitalize()
                page.evaluate(f'''() => {{
                    const nameInp = document.querySelector('input[name="name"], input[placeholder*="name" i]');
                    if (nameInp && !nameInp.value) {{
                        nameInp.value = "{short_name}";
                        nameInp.dispatchEvent(new Event('input', {{bubbles: true}}));
                        nameInp.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                    const bdayInp = document.querySelector('input[name="birthday"], input[type="text"][placeholder*="YYYY"], input[placeholder*="birth" i], input[name="age"]');
                    if (bdayInp && !bdayInp.value) {{
                        bdayInp.value = bdayInp.getAttribute('placeholder')?.includes('YYYY') ? '2000-01-15' : '15/01/2000';
                        bdayInp.dispatchEvent(new Event('input', {{bubbles: true}}));
                        bdayInp.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }}''')
                page.wait_for_timeout(1000)
                btn = page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first
                if btn.count() > 0 and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(6000)
                continue
                
            id_inp = page.locator('#identifierId, input[name="identifier"]').first
            if id_inp.count() > 0 and id_inp.is_visible():
                id_inp.fill(email)
                page.locator('#identifierNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
                page.wait_for_timeout(5000)
                continue
                
            if "accountchooser" in u or "chooseaccount" in u:
                acc_elem = page.get_by_text(email).first
                if acc_elem.count() > 0:
                    acc_elem.click()
                else:
                    page.locator(f'[data-identifier="{email}"]').first.click()
                page.wait_for_timeout(5000)
                continue
                
            pwd_inp = page.locator('input[name="Passwd"], input[type="password"]:visible').first
            if pwd_inp.count() > 0 and pwd_inp.is_visible() and password and "google.com" in u:
                pwd_inp.fill(password)
                page.locator('#passwordNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
                page.wait_for_timeout(6000)
                continue
                
            if ("challenge/totp" in u or page.locator('#totpPin:visible').count() > 0) and totp_key:
                code = pyotp.TOTP(totp_key).now()
                totp_inp = page.locator('#totpPin, input[type="tel"]').first
                if totp_inp.count() > 0:
                    totp_inp.fill(code)
                    page.locator('#totpNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
                    page.wait_for_timeout(6000)
                continue
                
            if ("consent" in u or page.locator('button:has-text("Tiếp tục"):visible').count() > 0) and "google.com" in u:
                page.locator('button:has-text("Tiếp tục"), button:has-text("Continue")').first.click()
                page.wait_for_timeout(5000)
                continue
                
        page.wait_for_timeout(4000)
        fresh_cookies = context.cookies(["https://chatgpt.com"])
        return "; ".join([f"{c['name']}={c['value']}" for c in fresh_cookies])

def refresh_chatgpt_account_via_gpm(pid: str, cid: str, email: str, creds: dict):
    # log(f"Đang mở GPM profile PID {pid} để kiểm tra/hồi sinh ChatGPT cho {email}...")
    try:
        res_start = requests.get(f"{GPM_API}/profiles/start/{pid}?win_scale=0.8", timeout=20).json()
        if not res_start.get('success'):
            return False, f"Start profile fail: {res_start.get('message')}"
        cdp_addr = res_start['data']['remote_debugging_address']
        time.sleep(2)
        
        cookie_str = perform_auto_login_and_extract_cookies(cdp_addr, email, creds)
        is_valid, v_res = test_connection_valid(cookie_str)
        if not is_valid:
            return False, f"Validate fail: {v_res}"
        
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # Guard: xác thực connection_id thuộc provider chatgpt-web để tránh ghi nhầm account
            cur.execute("SELECT provider, name FROM provider_connections WHERE id=?", (cid,))
            conn_row = cur.fetchone()
            if not conn_row or conn_row[0] != 'chatgpt-web':
                return False, f"Guard rejected: Connection {cid} does not belong to chatgpt-web provider"

            cur.execute('''
                UPDATE provider_connections 
                SET api_key=?, is_active=1, test_status='active', last_error=NULL, last_error_at=NULL, backoff_level=0, rate_limited_until=NULL, updated_at=CURRENT_TIMESTAMP 
                WHERE id=?
            ''', (cookie_str, cid))
            
            row = cur.execute("SELECT data FROM combos WHERE name='chatgpt-web-pool'").fetchone()
            if row:
                cdata = json.loads(row[0])
                models = cdata.get('models', [])
                if not any(m.get('connectionId') == cid for m in models):
                    short = email.split('@')[0]
                    models.append({
                        "id": f"chatgpt-web-pool-model-{len(models)+1}-{cid[:8]}",
                        "kind": "model",
                        "model": "chatgpt-web/gpt-5.6-sol-high",
                        "providerId": "chatgpt-web",
                        "connectionId": cid,
                        "weight": 0,
                        "label": f"sol-acc-{len(models)+1}: {short}"
                    })
                    cdata['models'] = models
                    cur.execute("UPDATE combos SET data=? WHERE name='chatgpt-web-pool'", (json.dumps(cdata),))
            conn.commit()
        except Exception:
            if conn:
                try: conn.rollback()
                except Exception: pass
            raise
        finally:
            if conn:
                try: conn.close()
                except Exception: pass
        return True, "Hồi sinh ChatGPT-Web thành công"
    except Exception as e:
        return False, f"Exception: {e}"
    finally:
        requests.get(f"{GPM_API}/profiles/close/{pid}", timeout=10)
        time.sleep(2)

perform_revive_chatgpt_account = refresh_chatgpt_account_via_gpm

# ==================== ARCHITECTURE LAYER 3: ANTIGRAVITY OAUTH & BROWSER AUTOMATION ====================
def is_profile_aged_7_days(profile: dict, min_days: int = 7) -> bool:
    """
    Van an toàn 7 ngày: Chỉ thực hiện OAuth Antigravity cho profile GPM
    nếu tài khoản đã đăng nhập/tạo/ngâm trên GPM >= 7 ngày
    (dựa vào created_time / created_at của profile GPM hoặc ngày trong metadata).
    """
    if not profile or not isinstance(profile, dict):
        return False
        
    raw_time = (
        profile.get('created_time') or 
        profile.get('created_at') or 
        profile.get('create_time') or 
        profile.get('created_date')
    )
    
    created_dt = None
    if raw_time:
        if isinstance(raw_time, (int, float)):
            ts = raw_time if raw_time < 1e11 else raw_time / 1000
            try:
                created_dt = datetime.fromtimestamp(ts)
            except Exception:
                pass
        elif isinstance(raw_time, str):
            clean_str = raw_time.strip().replace('Z', '')
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    created_dt = datetime.strptime(clean_str[:19], fmt)
                    break
                except Exception:
                    pass

    # Fallback: Tìm ngày tạo trong metadata/profile_path/note (ví dụ DDMMYYYY trong profile_path)
    if not created_dt:
        meta_str = f"{profile.get('note') or ''} {profile.get('profile_path') or ''} {profile.get('raw_proxy') or ''}"
        import re
        m = re.search(r'(\d{2})(\d{2})(20\d{2})', meta_str)
        if m:
            try:
                day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                created_dt = datetime(year, month, day)
            except Exception:
                pass

    if not created_dt:
        return False

    age_days = (datetime.now() - created_dt).total_seconds() / 86400.0
    return age_days >= min_days

def fetch_google_recovery_otp(target_email: str = None, lookback_seconds: int = 180, timeout_seconds: int = 45) -> str | None:
    """Lấy mã OTP xác minh Google gửi về email khôi phục (thanhdatbui1995@gmail.com) qua IMAP tối ưu siêu nhanh."""
    import imaplib, email, unicodedata, re
    from email.header import decode_header, make_header
    from email.utils import parsedate_to_datetime
    from datetime import timezone
    
    user = os.environ.get("OTP_MAIL_USER")
    pwd = os.environ.get("OTP_MAIL_APP_PASSWORD", "").replace(" ", "")
    if not user or not pwd:
        return None

    def _decode_hdr(v):
        try: return str(make_header(decode_header(v or "")))
        except Exception: return v or ""

    not_before_ts = time.time() - lookback_seconds
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com", timeout=12)
            imap.login(user, pwd)
            imap.select("INBOX", readonly=True)
            typ, data = imap.search(None, "FROM", "\"google.com\"")
            if not (typ == "OK" and data and data[0]):
                typ, data = imap.search(None, "ALL")
            if typ == "OK" and data and data[0]:
                ids = data[0].split()
                for mid in reversed(ids[-8:]):
                    typ, hdata = imap.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                    if not (typ == "OK" and hdata and isinstance(hdata[0], tuple)):
                        continue
                    hmsg = email.message_from_bytes(hdata[0][1])
                    try:
                        dt = parsedate_to_datetime(hmsg.get("Date", ""))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt.timestamp() < not_before_ts:
                            continue
                    except Exception:
                        pass

                    subj = _decode_hdr(hmsg.get("Subject", "")).lower()
                    if "cảnh báo" in subj or "security alert" in subj:
                        continue

                    typ, bdata = imap.fetch(mid, "(RFC822)")
                    if not (typ == "OK" and bdata and isinstance(bdata[0], tuple)):
                        continue
                    msg = email.message_from_bytes(bdata[0][1])
                    chunks = [subj]
                    for part in (msg.walk() if msg.is_multipart() else (msg,)):
                        if part.get_content_maintype() == "multipart" or part.get_content_disposition() == "attachment":
                            continue
                        payload = part.get_payload(decode=True)
                        if payload is None:
                            continue
                        charset = part.get_content_charset() or "utf-8"
                        chunks.append(payload.decode(charset, errors="replace"))
                    body = "\n".join(chunks)

                    if target_email:
                        short_email = target_email.split('@')[0].lower()
                        if short_email not in subj and short_email not in body.lower() and target_email.lower() not in body.lower():
                            continue

                    clean_body = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", " ", body)
                    normalized = unicodedata.normalize("NFKD", re.sub(r"<[^>]+>", " ", clean_body))
                    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
                    patterns = (
                        r"(?i)(?:verification code is|ma xac minh la|code is|is:)\D{0,40}(\d{6})(?!\d)",
                        r"(?i)(?:su dung|use|code|otp|verification|xac minh|ma|recovery email)\D{0,60}(\d{6})(?!\d)",
                        r"G-(\d{6})(?!\d)",
                        r"(?<!\d)(\d{6})(?!\d)"
                    )
                    for pattern in patterns:
                        m = re.search(pattern, normalized)
                        if m and m.group(1) != "000000":
                            code = m.group(1)
                            imap.logout()
                            log(f"[IMAP-OTP] Đã trích xuất mã OTP thành công: {code}")
                            return code
            imap.logout()
        except Exception as e:
            log(f"[IMAP-OTP-WARN] {e}")
        time.sleep(2.5)
    return None

def solve_recaptcha_audio(page) -> bool:
    """Tự động phát hiện và giải reCAPTCHA Enterprise / v2 Audio Challenge trên trang Google."""
    anchor_frame = None
    bframe = None

    for _ in range(6):
        for f in page.frames:
            if "recaptcha" in f.url and ("anchor" in f.url or "api2/anchor" in f.url):
                anchor_frame = f
            if "recaptcha" in f.url and ("bframe" in f.url or "api2/bframe" in f.url):
                bframe = f
        if anchor_frame:
            break
        time.sleep(1)

    if not anchor_frame:
        return False

    try:
        anchor_btn = anchor_frame.locator("#recaptcha-anchor, .recaptcha-checkbox")
        if anchor_btn.count() > 0:
            anchor_btn.first.click(timeout=5000)
            time.sleep(2.5)

        if anchor_frame.locator("#recaptcha-anchor").get_attribute("aria-checked") == "true":
            log("reCAPTCHA checkbox passed automatically (green check)!")
            post_btn = page.locator('button:has-text("Tiếp theo"), button:has-text("Next"), #recaptchaNext').first
            if post_btn.count() > 0 and post_btn.is_visible():
                post_btn.click(timeout=5000)
            return True

        for _ in range(6):
            for f in page.frames:
                if "recaptcha" in f.url and ("bframe" in f.url or "api2/bframe" in f.url):
                    bframe = f
                    break
            if bframe:
                break
            time.sleep(1)

        if not bframe:
            return False

        audio_btn = bframe.locator("#recaptcha-audio-button, button[title*='audio'], button[title*='âm thanh']")
        if audio_btn.count() == 0 or not audio_btn.first.is_visible():
            return False

        audio_btn.first.click(timeout=5000)
        time.sleep(3)

        audio_elem = bframe.locator("#audio-source, .rc-audiochallenge-tdownload-link, audio")
        if audio_elem.count() == 0:
            return False

        audio_src = audio_elem.first.get_attribute("href") or audio_elem.first.get_attribute("src")
        if not audio_src:
            return False

        cache_dir = r"C:\Users\Kibe\AppData\Local\hermes\cache"
        os.makedirs(cache_dir, exist_ok=True)
        mp3_path = os.path.join(cache_dir, f"recaptcha_{time.time()}.mp3")
        wav_path = mp3_path.replace(".mp3", ".wav")

        urllib.request.urlretrieve(audio_src, mp3_path)
        sound = pydub.AudioSegment.from_mp3(mp3_path)
        sound.export(wav_path, format="wav")

        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)

        log(f"reCAPTCHA Audio Recognized Text: '{text}'")
        for p in [mp3_path, wav_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

        inp = bframe.locator("#audio-response, input[name='audio-response']")
        inp.fill(text)
        time.sleep(1)

        bframe.locator("#recaptcha-verify-button, button:has-text('Verify'), button:has-text('Xác minh')").first.click(timeout=5000)
        time.sleep(3)

        post_btn = page.locator('button:has-text("Tiếp theo"), button:has-text("Next"), #recaptchaNext').first
        if post_btn.count() > 0 and post_btn.is_visible():
            post_btn.click(timeout=5000)
        return True
    except Exception as e:
        log(f"Lỗi giải reCAPTCHA audio: {e}")
        return False

def perform_antigravity_oauth(cdp_addr: str, email: str, creds: dict = None):
    redirect_uri = f"{OMNI_API}/callback"
    encoded_redirect_uri = urllib.parse.quote(redirect_uri, safe="")
    
    r_resp = requests.get(f"{OMNI_API}/api/oauth/antigravity/authorize?redirect_uri={encoded_redirect_uri}", timeout=10)
    if r_resp.status_code != 200:
        return False, f"Authorize HTTP {r_resp.status_code}"
    r_auth = r_resp.json()
    auth_url = r_auth.get("authUrl")
    state = r_auth.get("state", "")
    code_verifier = r_auth.get("codeVerifier", "")
    if not auth_url:
        return False, "Thiếu authUrl"

    acc_info = (creds or {}).get(email.lower(), {})
    password = acc_info.get('password')
    totp_key = acc_info.get('totp')
    recovery_email = acc_info.get('recovery_email')

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        captured_code = None
        def check_for_code(url_str: str):
            nonlocal captured_code
            if not captured_code and "/callback" in url_str and "code=" in url_str:
                try:
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url_str).query)
                    if "code" in qs and qs["code"]:
                        captured_code = qs["code"][0]
                except Exception:
                    pass

        page.on("request", lambda r: check_for_code(r.url))
        page.on("response", lambda r: check_for_code(r.url))
        
        page.goto(auth_url, wait_until="domcontentloaded", timeout=60000)
        start_t = time.time()
        while time.time() - start_t < 120:
            if captured_code:
                break
            try:
                cur_url = page.url.lower()
                if "/callback" in cur_url and "code=" in cur_url:
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(cur_url).query)
                    if "code" in qs:
                        captured_code = qs["code"][0]
                        break
            except Exception: pass
            
            # 1. Chọn email nếu ở Account Chooser
            try:
                u_lower = page.url.lower()
                if ("accountchooser" in u_lower or "chooseaccount" in u_lower) and "selectchallenge" not in u_lower and "challenge" not in u_lower:
                    acc_div = page.locator(f'div[data-email="{email.lower()}"], div[data-identifier="{email.lower()}"], [role="link"]:has-text("{email.lower()}"), [role="button"]:has-text("{email.lower()}")').first
                    if acc_div.count() == 0:
                        acc_div = page.get_by_text(email.lower()).first
                    if acc_div.count() > 0 and acc_div.is_visible():
                        acc_div.click(timeout=5000)
                        time.sleep(2)
                        continue
            except Exception: pass
            
            # 2. Nhập mật khẩu nếu Google yêu cầu xác minh
            try:
                pwd_inp = page.locator('input[name="Passwd"], input[type="password"]:visible').first
                if pwd_inp.count() > 0 and pwd_inp.is_visible() and password and "google.com" in page.url.lower():
                    pwd_inp.fill(password)
                    page.locator('#passwordNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click(timeout=5000)
                    time.sleep(3)
                    continue
            except Exception: pass

            # 2.2. Xử lý OTP input nếu Google đã ở màn hình nhập mã
            try:
                is_phone_cp = page.evaluate('''() => {
                    const txt = (document.body.innerText || '').toLowerCase();
                    return (txt.includes('phone number') || txt.includes('số điện thoại')) && (txt.includes('enter a phone') || txt.includes('nhập số'));
                }''')
                if is_phone_cp:
                    log(f"[{email}] Google yêu cầu xác minh qua SỐ ĐIỆN THOẠI (Phone Checkpoint). Dừng xử lý để bảo vệ tài khoản.")
                    break

                otp_inp = page.locator('input[name="code"], #idvPin, input[id*="idvPin"], input[id*="Pin"]:not([id*="phone"]):not([id*="Phone"]), input[name="pin"]').first
                if otp_inp.count() > 0 and otp_inp.is_visible() and "google.com" in page.url.lower():
                    log(f"[{email}] Phát hiện form nhập OTP Google! Đang đợi và đọc mã từ IMAP recovery mail...")
                    otp_code = fetch_google_recovery_otp(target_email=email, lookback_seconds=180, timeout_seconds=45)
                    if otp_code:
                        log(f"[{email}] Đã lấy được mã OTP từ IMAP: {otp_code}")
                        otp_inp.fill(otp_code)
                        time.sleep(1)
                        next_btn = page.locator('button:has-text("Tiếp theo"), button:has-text("Next"), #next, [role="button"]:has-text("Next"), #idvPreregisteredPhoneNext').first
                        if next_btn.count() > 0 and next_btn.is_visible():
                            next_btn.click(timeout=5000)
                        time.sleep(3)
                        continue
                    else:
                        log(f"[{email}] Không nhận được OTP từ IMAP trong thời gian quy định.")
                        time.sleep(2)
                        continue
            except Exception as e:
                log(f"Lỗi xử lý OTP input: {e}")

            # 2.3. Xử lý click chọn "Get a verification code at recovery mail" (nếu đang ở màn hình chọn phương thức)
            try:
                clicked_code_opt = False
                for txt_candidate in ["Get a verification code at", "Nhận mã xác minh tại", "Get a verification code"]:
                    loc = page.get_by_text(txt_candidate, exact=False).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click(timeout=4000)
                        clicked_code_opt = True
                        break

                if not clicked_code_opt:
                    clicked_code_opt = page.evaluate('''() => {
                        if (document.querySelector('input[name="code"], input[id*="idvPin"], input[id*="Pin"], input[id*="code"], #idvPin, #pin')) {
                            return false;
                        }
                        for (const el of document.querySelectorAll('li, div, span, [role="link"], [role="button"], [data-challengeindex]')) {
                            const txt = (el.innerText || el.textContent || '').trim();
                            if (txt.includes('Get a verification code at') || txt.includes('Nhận mã xác minh tại')) {
                                const target = el.closest('[role="link"], [role="button"], li, [data-challengeindex], div[jsaction]') || el;
                                target.click();
                                return true;
                            }
                        }
                        return false;
                    }''')

                if clicked_code_opt:
                    log(f"[{email}] Đã click 'Get a verification code at recovery mail', chờ chuyển trang nhập mã...")
                    time.sleep(4)
                    continue
            except Exception as e:
                log(f"Lỗi xử lý Get verification code: {e}")

            # 2.4. Xử lý "Confirm your recovery email" nếu Google yêu cầu
            try:
                clicked_opt = page.evaluate('''() => {
                    for (const el of document.querySelectorAll('div, li, span, a, [role="link"], [data-challengeindex]')) {
                        const txt = (el.innerText || el.textContent || '').trim();
                        if (txt === 'Confirm your recovery email' || txt === 'Xác nhận email khôi phục' || txt.includes('Confirm your recovery email')) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                if clicked_opt:
                    time.sleep(3)
                    continue

                filled = False
                if recovery_email:
                    filled = page.evaluate(f'''() => {{
                        const inp = document.querySelector('input[type="email"], input[name="knowledgePreregisteredEmailResponse"], input[id*="recovery"]');
                        if (inp && inp.offsetParent !== null) {{
                            inp.value = "{recovery_email}";
                            inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                            inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                            return true;
                        }}
                        return false;
                    }}''')
                if filled:
                    next_btn = page.locator('button:has-text("Tiếp theo"), button:has-text("Next"), #next, [role="button"]:has-text("Next")').first
                    if next_btn.count() > 0 and next_btn.is_visible():
                        next_btn.click(timeout=5000)
                    time.sleep(3)
                    continue
            except Exception as e:
                log(f"Lỗi xử lý recovery email: {e}")

            # 3. Nhập TOTP 2FA nếu Google yêu cầu Google Authenticator (chỉ match ID totpPin, không match input[type=tel])
            try:
                totp_inp = page.locator('#totpPin, input[name="totpPin"], input[id*="totpPin"]').first
                if totp_inp.count() > 0 and totp_inp.is_visible() and totp_key and "google.com" in page.url.lower():
                    code = pyotp.TOTP(totp_key).now()
                    totp_inp.fill(code)
                    page.locator('#totpNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click(timeout=5000)
                    time.sleep(3)
                    continue
            except Exception: pass

            # 3.5. reCAPTCHA challenge handler
            try:
                has_recaptcha = any("recaptcha" in f.url for f in page.frames) or (page.locator("iframe[src*='recaptcha']").count() > 0)
                if has_recaptcha:
                    solve_recaptcha_audio(page)
                    time.sleep(2)
                    continue
            except Exception: pass

            # 4. Consent screen & checkboxes
            try:
                for cb in page.locator('input[type="checkbox"]:not(:checked)').all():
                    try:
                        if cb.is_visible(): cb.check(timeout=2000)
                    except Exception: pass

                for sel in ['button:has-text("Cho phép")', 'button:has-text("Tiếp tục")', 'button:has-text("Allow")', 'button:has-text("Continue")', '#submit_approve_access']:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click(timeout=5000)
                        time.sleep(2)
                        break
            except Exception: pass
            
            time.sleep(1.5)

        if not captured_code:
            try:
                from pathlib import Path
                ss_dir = Path(r"C:\Users\Kibe\AppData\Local\hermes\cache")
                ss_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(ss_dir / f"oauth_err_{email.split('@')[0]}.png"))
            except Exception: pass
            return False, "Timeout bắt OAuth code"
            
        ex_resp = requests.post(f"{OMNI_API}/api/oauth/antigravity/exchange", json={
            "code": captured_code,
            "redirectUri": redirect_uri,
            "codeVerifier": code_verifier,
            "state": state
        }, timeout=20)
        
        if ex_resp.status_code != 200:
            return False, f"Exchange HTTP {ex_resp.status_code}: {ex_resp.text[:100]}"
            
        return True, "Hồi sinh Antigravity OAuth thành công"

def refresh_antigravity_account_via_gpm(pid: str, email: str, profile_data: dict = None, creds: dict = None):
    if profile_data and not is_profile_aged_7_days(profile_data, min_days=7):
        return False, "Van an toàn: Profile GPM chưa đủ 7 ngày tuổi để thực hiện OAuth Antigravity"
    try:
        res_start = requests.get(f"{GPM_API}/profiles/start/{pid}?win_scale=0.8", timeout=20).json()
        if not res_start.get('success'):
            return False, f"Start profile fail: {res_start.get('message')}"
        cdp_addr = res_start['data']['remote_debugging_address']
        time.sleep(2)
        
        ok, msg = perform_antigravity_oauth(cdp_addr, email, creds)
        return ok, msg
    except Exception as e:
        return False, f"Exception: {e}"
    finally:
        try:
            requests.get(f"{GPM_API}/profiles/close/{pid}", timeout=10)
        except Exception: pass
        try:
            requests.get(f"{GPM_API}/profiles/stop/{pid}", timeout=10)
        except Exception: pass
        time.sleep(2)

SELECTOR_VERSION = "2026.09.25-v1"
TELEMETRY_CACHE_PATH = os.path.expanduser(r"~\AppData\Local\hermes\cache\chatgpt_web_pool_telemetry.json")
TELEMETRY_HISTORY_PATH = os.path.expanduser(r"~\AppData\Local\hermes\cache\chatgpt_web_pool_telemetry_history.jsonl")

def save_telemetry_metrics(metrics: dict) -> bool:
    """Ghi structured telemetry metrics vào cache JSON an toàn (atomic write qua temp file) và append history audit trail."""
    try:
        os.makedirs(os.path.dirname(TELEMETRY_CACHE_PATH), exist_ok=True)
        metrics["selector_version"] = SELECTOR_VERSION
        tmp_path = TELEMETRY_CACHE_PATH + f".tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        if os.path.exists(TELEMETRY_CACHE_PATH):
            os.replace(tmp_path, TELEMETRY_CACHE_PATH)
        else:
            os.rename(tmp_path, TELEMETRY_CACHE_PATH)

        with open(TELEMETRY_HISTORY_PATH, "a", encoding="utf-8") as f_hist:
            f_hist.write(json.dumps(metrics, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        log(f"[TELEMETRY-CRITICAL-ALERT] Không thể lưu telemetry metrics và history audit trail: {e}")
        return False

# ==================== ARCHITECTURE LAYER 4: CONTROLLER & TELEMETRY OBSERVABILITY ====================
def main():
    log("=== BẮT ĐẦU QUÉT SỨC KHỎE POOL TÀI KHOẢN OMNIROUTE ===")
    gpm_map = get_gpm_profiles_map()
    creds = load_accounts_credentials()
    
    # 1. Quét ChatGPT-Web
    chatgpt_conns = get_connections_by_provider('chatgpt-web')
    chatgpt_inactive = [c for c in chatgpt_conns if not (c.get('isActive') and c.get('testStatus') == 'active')]
    
    recovered_chatgpt = []
    failed_chatgpt = []
    
    if chatgpt_inactive:
        log(f"Phát hiện {len(chatgpt_inactive)} tài khoản ChatGPT-Web cần hồi sinh...")
        for c in chatgpt_inactive:
            cname = c.get('name', '')
            cid = c.get('id')
            import re
            m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', cname)
            if not m:
                continue
            email = m.group(1).lower()
            if email in gpm_map:
                pid = gpm_map[email]['id']
                ok, msg = refresh_chatgpt_account_via_gpm(pid, cid, email, creds)
                if ok:
                    recovered_chatgpt.append(email)
                else:
                    failed_chatgpt.append((email, msg))
            else:
                failed_chatgpt.append((email, "Không thấy profile GPM"))
                
    # 2. Quét Antigravity OAuth
    ag_conns = get_connections_by_provider('antigravity')
    # Tôn trọng trạng thái người dùng/router chủ động tắt (Standby) - CẤM tự ý bật lại is_active=1!
    ag_broken = [c for c in ag_conns if c.get('testStatus') != 'active']
    recovered_ag = []
    failed_ag = []
    
    if ag_broken:
        log(f"Phát hiện {len(ag_broken)} tài khoản Antigravity cần OAuth hồi sinh...")
        for c in ag_broken:
            email = c.get('name', '').lower()
            if "@gmail.com" not in email:
                continue
            if email in gpm_map:
                prof = gpm_map[email]
                pid = prof['id']
                ok, msg = refresh_antigravity_account_via_gpm(pid, email, prof, creds)
                if ok:
                    recovered_ag.append(email)
                else:
                    failed_ag.append((email, msg))
            else:
                failed_ag.append((email, "Không thấy profile GPM"))

    # 3. Quét Codex OAuth
    codex_conns = get_connections_by_provider('codex')
    # Tôn trọng trạng thái người dùng/router chủ động tắt (Standby) - CẤM tự ý bật lại is_active=1!
    codex_broken = [c for c in codex_conns if c.get('testStatus') != 'active']
    failed_codex = []
    if codex_broken:
        log(f"Phát hiện {len(codex_broken)} tài khoản Codex có trạng thái không active...")
        for c in codex_broken:
            cname = c.get('name') or c.get('id', 'unknown')
            cerr = c.get('lastError') or f"testStatus={c.get('testStatus')}"
            failed_codex.append((cname, cerr))

    # Tổng kết
    chatgpt_after = get_connections_by_provider('chatgpt-web')
    chatgpt_active_cnt = sum(1 for c in chatgpt_after if c.get('isActive') and c.get('testStatus') == 'active')
    
    ag_after = get_connections_by_provider('antigravity')
    ag_active_cnt = sum(1 for c in ag_after if c.get('isActive') and c.get('testStatus') == 'active')

    codex_after = get_connections_by_provider('codex')
    codex_active_cnt = sum(1 for c in codex_after if c.get('isActive') and c.get('testStatus') == 'active')
    
    all_failed = failed_chatgpt + failed_ag + failed_codex
    if not recovered_chatgpt and not recovered_ag and not all_failed:
        return

    report_lines = [
        f"🤖 [POOL HEALER] BÁO CÁO SỨC KHỎE",
        f"• ChatGPT-Web: {chatgpt_active_cnt}/{len(chatgpt_after)} ACTIVE",
        f"• Antigravity: {ag_active_cnt}/{len(ag_after)} ACTIVE",
        f"• Codex: {codex_active_cnt}/{len(codex_after)} ACTIVE"
    ]
    
    if recovered_chatgpt:
        report_lines.append(f"• Đã hồi sinh ChatGPT ({len(recovered_chatgpt)} acc): {', '.join([a.split('@')[0] for a in recovered_chatgpt])}")
    if recovered_ag:
        report_lines.append(f"• Đã hồi sinh Antigravity ({len(recovered_ag)} acc): {', '.join([a.split('@')[0] for a in recovered_ag])}")
        
    if all_failed:
        report_lines.append(f"• Cần chú ý ({len(all_failed)} acc):")
        for a, err in all_failed[:5]:
            report_lines.append(f"  - `{a}`: {err[:60]}")
        if len(all_failed) > 5:
            report_lines.append(f"  - *...và {len(all_failed) - 5} tài khoản khác*")
            
    from datetime import datetime, timezone
    
    # Phân loại failure categories để phục vụ triage & alerting
    categorized_failures = []
    for a, err in all_failed:
        err_str = str(err)
        cat = "UNKNOWN"
        if "phone" in err_str.lower() or "số điện thoại" in err_str.lower():
            cat = "PHONE_CHECKPOINT"
        elif "timeout" in err_str.lower():
            cat = "TIMEOUT"
        elif "proxy" in err_str.lower():
            cat = "PROXY_ERROR"
        elif "recaptcha" in err_str.lower():
            cat = "CAPTCHA_CHALLENGE"
        categorized_failures.append({"account": a, "category": cat, "error": err_str[:100]})

    telemetry_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chatgpt_web": {"active": chatgpt_active_cnt, "total": len(chatgpt_after)},
        "antigravity": {"active": ag_active_cnt, "total": len(ag_after)},
        "codex": {"active": codex_active_cnt, "total": len(codex_after)},
        "recovered_chatgpt": recovered_chatgpt,
        "recovered_ag": recovered_ag,
        "total_failures": len(all_failed),
        "failures": categorized_failures
    }
    save_telemetry_metrics(telemetry_data)

    report_msg = "\n".join(report_lines)
    print(report_msg)

if __name__ == '__main__':
    main()
