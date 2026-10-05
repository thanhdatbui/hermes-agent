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
import socket
import sqlite3
import msvcrt
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
import requests
import pyotp
import openpyxl
import pydub
import speech_recognition as sr
from playwright.sync_api import sync_playwright

def log(msg: str):
    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()

sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
try:
    from run_oauth_s7_pipeline import get_s7_security_code, approve_s7_google_prompt, get_account_for_email
except (ImportError, ModuleNotFoundError) as e:
    log(f"[OPTIONAL] GPM S7 pipeline unavailable: {type(e).__name__}")
    get_s7_security_code, approve_s7_google_prompt, get_account_for_email = None, None, None


class CodexOAuth1455Lock:
    def __init__(self, lock_file="D:/Taadaa/runtime/kibe/cron-state/codex_oauth_1455.lock", timeout=900):
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self.handle = None

    def __enter__(self):
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        start_t = time.time()
        self.handle = open(self.lock_file, "a+b")
        waited = False
        while True:
            try:
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                if waited:
                    log(f"[CODEX-1455-LOCK] Đã lấy khóa sau {time.time()-start_t:.1f}s")
                return self
            except (OSError, IOError):
                if not waited:
                    log("[CODEX-1455-LOCK] Đang chờ nhả khóa độc quyền cổng 1455...")
                    waited = True
                if time.time() - start_t > self.timeout:
                    raise TimeoutError(f"Timeout {self.timeout}s waiting for Codex OAuth 1455 lock")
                time.sleep(2)

    def __exit__(self, *_):
        if self.handle:
            try:
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, IOError):
                pass
            try:
                self.handle.close()
            except (OSError, IOError):
                pass
            self.handle = None


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
UPDATED_XLSX_PATH = r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"
if not os.path.exists(UPDATED_XLSX_PATH):
    UPDATED_XLSX_PATH = r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated.xlsx"
DIRECT_OAUTH_URL = "https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true"

def get_chatgpt_password_from_workbook(email: str) -> str:
    """Đọc mật khẩu ChatGPT chính chủ từ cột L (PASS CHATGPT) trong workbook taikhoan_dat_v2_updated."""
    if not os.path.exists(UPDATED_XLSX_PATH):
        return ""
    try:
        wb = openpyxl.load_workbook(UPDATED_XLSX_PATH, read_only=True, data_only=True)
        ws = wb["Tài Khoản"] if "Tài Khoản" in wb.sheetnames else wb.active
        em_lower = email.strip().lower()
        for row in ws.iter_rows(values_only=True):
            if not row or len(row) < 6:
                continue
            row_gmail = str(row[5] or "").strip().lower()
            if row_gmail == em_lower:
                p_chatgpt = str(row[11] or "").strip() if len(row) > 11 and row[11] else ""
                wb.close()
                if p_chatgpt:
                    return p_chatgpt
        wb.close()
    except (IOError, openpyxl.utils.exceptions.InvalidFileException, KeyError) as e:
        log(f"Lỗi đọc PASS CHATGPT cho {email}: {type(e).__name__}")
    return ""

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
    except (IOError, openpyxl.utils.exceptions.InvalidFileException, KeyError) as e:
        log(f"Lỗi đọc credentials từ Excel: {type(e).__name__}")
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

def codex_oauth_invalid_reason(connection: dict):
    """Classify only recorded, unambiguous OAuth invalidation evidence."""
    if not isinstance(connection, dict):
        return None
    for field in ("httpStatus", "statusCode", "http_code", "errorCode", "error_code"):
        value = connection.get(field)
        if isinstance(value, bool):
            continue
        try:
            if int(value) == 401:
                return f"{field}=401"
        except (TypeError, ValueError):
            pass
    for field in ("errorType", "error_type", "type"):
        value = connection.get(field)
        if isinstance(value, str) and value.strip().lower() == "upstream_auth_error":
            return f"{field}=upstream_auth_error"
    last_error = connection.get("lastError")
    if isinstance(last_error, str) and any(
        marker in last_error.lower() for marker in ("token invalid", "token revoked")
    ):
        return "lastError contains Token invalid/revoked"
    return None


def disable_codex_connection(connection: dict, reason: str) -> bool:
    """Disable one verified Codex connection via the existing DB pattern."""
    cid = connection.get("id") if isinstance(connection, dict) else None
    if not cid or connection.get("isActive") is not True:
        return False
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        row = cur.execute(
            "SELECT provider FROM provider_connections WHERE id=?", (cid,)
        ).fetchone()
        if not row or row[0] != "codex":
            log(f"[CODEX-DISABLE-SKIP] provider guard rejected {cid}")
            return False
        cur.execute(
            "UPDATE provider_connections SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (cid,),
        )
        if cur.rowcount != 1:
            return False
        conn.commit()
        log(f"[CODEX-DISABLED] {connection.get('name') or cid}: {reason}")
        return True
    except sqlite3.DatabaseError as e:
        if conn:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        log(f"[CODEX-DISABLE-ERROR] {connection.get('name') or cid}: DB error")
        return False
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        log(f"[CODEX-DISABLE-ERROR] {connection.get('name') or cid}: {type(e).__name__}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except sqlite3.Error:
                pass

def get_gpm_profiles():
    try:
        profiles = []
        page = 1
        total_pages = None
        expected_total = None
        while True:
            res = requests.get(f"{GPM_API}/profiles?page={page}&per_page=50", timeout=10).json()
            pagination = res.get('pagination') or {}
            page_total = pagination.get('total_page')
            if not isinstance(page_total, int) or page_total < 1:
                raise ValueError(f"invalid GPM pagination total_page={page_total!r}")
            if total_pages is None:
                total_pages = page_total
                expected_total = pagination.get('total', pagination.get('total_count'))
                if expected_total is not None and (not isinstance(expected_total, int) or expected_total < 0):
                    raise ValueError(f"invalid GPM pagination total={expected_total!r}")
            elif page_total != total_pages:
                raise ValueError(f"GPM pagination total_page changed: {total_pages} -> {page_total}")

            data = res.get('data')
            if not isinstance(data, list) or not data:
                raise ValueError(f"GPM page {page}/{total_pages} returned no data")
            profiles.extend(data)
            if page == total_pages:
                break
            page += 1

        if expected_total is not None and len(profiles) != expected_total:
            raise ValueError(f"GPM profile count mismatch: fetched {len(profiles)}, expected {expected_total}")
        log(f"[GPM-PROFILES] fetched {len(profiles)} profiles across {total_pages} pages")
        return profiles
    except Exception as e:
        log(f"Lỗi lấy GPM profiles (fail-closed): {e}")
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
                email_map.setdefault(email, []).append(p)
        duplicates = {email: candidates for email, candidates in email_map.items() if len(candidates) > 1}
        if duplicates:
            for email, candidates in duplicates.items():
                log(f"[GPM-DUPLICATE] {email}: " + ", ".join(
                    f"id={p.get('id')}, profile_path={p.get('profile_path')}, created_at={p.get('created_at') or p.get('created_time')}"
                    for p in candidates
                ))
        log(f"[GPM-PROFILES] total fetched={len(profiles)}, duplicate accounts={len(duplicates)}")
        return email_map
    except Exception as e:
        log(f"Lỗi lấy GPM profiles map: {e}")
        return {}

def get_unambiguous_gpm_profile(gpm_map, email):
    candidates = gpm_map.get(email, [])
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        details = "; ".join(
            f"id={p.get('id')}, profile_path={p.get('profile_path')}, created_at={p.get('created_at') or p.get('created_time')}"
            for p in candidates
        )
        log(f"[AMBIGUOUS_GPM_PROFILE] {email}: {details}")
    return None

def test_connection_valid(cookie_str: str):
    if not cookie_str or not isinstance(cookie_str, str):
        return False, "EMPTY_SESSION_TOKEN"
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
    # Ưu tiên lấy pass ChatGPT từ workbook, nếu không có mới fallback về pass mail
    password = get_chatgpt_password_from_workbook(email) or acc_info.get('password')
    totp_key = acc_info.get('totp')
    
    with sync_playwright() as p:
        browser = None
        for attempt in range(1, 4):
            try:
                browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
                break
            except Exception as e:
                log(f"[{email}] CDP retry {attempt}/3 fail: {e}")
                time.sleep(attempt * 1.5)
        if not browser:
            log(f"[{email}] Kết nối CDP thất bại sau 3 lần thử")
            return None
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            page.goto("https://chatgpt.com/auth/login", timeout=35000, wait_until="domcontentloaded")
            os.makedirs(r"D:\Taadaa\GPM auto\debug_screenshots", exist_ok=True)
            page.screenshot(path=f"D:/Taadaa/GPM auto/debug_screenshots/canary_{email.split('@')[0]}_before.png")
        except Exception:
            pass
        page.wait_for_timeout(3000)
        
        # 1. Dismiss Cookie Banner triệt để
        try:
            cb = page.locator('button:has-text("Chấp nhận tất cả"), button:has-text("Accept all"), button:has-text("Allow all"), button:has-text("Accept")').first
            if cb.count() > 0 and cb.is_visible():
                cb.click(force=True)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # 2. Kiểm tra nếu có sẵn session sống trong trình duyệt
        def _get_clean_session_token():
            cookies = context.cookies(["https://chatgpt.com"])
            s_tok = None
            chunks = {}
            for c in cookies:
                cn, cv = c.get("name", ""), c.get("value", "")
                if cn == "__Secure-next-auth.session-token":
                    s_tok = cv
                    break
                elif cn.startswith("__Secure-next-auth.session-token."):
                    chunks[cn.split(".")[-1]] = cv
            if not s_tok and chunks:
                s_tok = "".join(chunks[k] for k in sorted(chunks.keys(), key=lambda x: int(x) if x.isdigit() else x))
            return s_tok

        # Kiểm tra nếu trang đã ở màn hình chính và không có chữ Log in
        b_text = ""
        try: b_text = page.locator("body").inner_text()
        except Exception: pass
        token = _get_clean_session_token()
        if token and token.startswith("eyJhbG") and "chatgpt.com" in page.url and "/auth/" not in page.url and "session has expired" not in b_text.lower():
            is_valid, _ = test_connection_valid(token)
            if is_valid:
                return token

        log(f"[{email}] Phiên hết hạn/văng session -> Bắt đầu tự động đăng nhập bằng Email + Password...")
        
        try:
            context.clear_cookies()
            page.goto("https://chatgpt.com/auth/login", timeout=35000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
        except Exception:
            pass
        try:
            for l_sel in ['button[data-testid="login-button"]', 'button:has-text("Log in")', 'button:has-text("Đăng nhập")', 'a:has-text("Log in")', 'a:has-text("Đăng nhập")']:
                l_btn = page.locator(l_sel).first
                if l_btn.count() > 0 and l_btn.is_visible():
                    l_btn.click(force=True)
                    page.wait_for_timeout(2500)
                    break
        except Exception:
            pass

        # 3. ĐIỀN EMAIL VÀO FORM ĐĂNG NHẬP
        email_inp = page.locator('input#email-input, input[name="email"], input[type="email"], input[name="username"]').first
        if email_inp.count() > 0 and email_inp.is_visible():
            email_inp.fill(email)
            page.wait_for_timeout(500)
            submit_btn = page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first
            if submit_btn.count() > 0:
                submit_btn.click(force=True)
                page.wait_for_timeout(3000)

        # 4. ĐIỀN PASSWORD NẾU OPENAI HỎI
        pwd_inp = page.locator('input#password, input[name="password"], input[type="password"]').first
        if pwd_inp.count() > 0 and pwd_inp.is_visible() and password:
            log(f"[{email}] Điền mật khẩu ChatGPT chính chủ...")
            pwd_inp.fill(password)
            page.wait_for_timeout(500)
            pwd_btn = page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first
            if pwd_btn.count() > 0:
                pwd_btn.click(force=True)
                page.wait_for_timeout(5000)
        else:
            # Nếu OpenAI tự chuyển sang Google SSO
            g_btn = page.locator('button[data-provider="google"], button:has-text("Continue with Google"), button:has-text("Tiếp tục với Google")').first
            if g_btn.count() > 0 and g_btn.is_visible():
                g_btn.click(force=True)
                page.wait_for_timeout(3000)

        # 5. XỬ LÝ CHUYỂN HƯỚNG GOOGLE HOẶC ONBOARDING (NẾU CÓ)
        for step in range(20):
            page.wait_for_timeout(2000)
            u = page.url.lower()
            
            # Kiểm tra tài khoản bị vô hiệu hóa
            if "payload=" in u and ("account_deactivated" in u or "accountdeactivated" in u):
                log(f"[{email}] CẢNH BÁO: Tài khoản OpenAI đã bị vô hiệu hóa (AccountDeactivated)!")
                return None
                
            if "chatgpt.com" in u and "/auth/" not in u:
                break
                
            if "accounts.google.com" in u and ("accountchooser" in u or "identifier" in u):
                acc_elem = page.locator(f'[data-identifier*="{email}"]').first
                if acc_elem.count() == 0:
                    acc_elem = page.locator('div[data-identifier*="@gmail.com"]').first
                if acc_elem.count() > 0:
                    acc_elem.click(force=True)
                    page.wait_for_timeout(3000)
                    continue
                    
            if ("consent" in u or "/oauth/id" in u) and "google.com" in u:
                c_btn = page.locator('button:has-text("Tiếp tục"), button:has-text("Continue")').first
                if c_btn.count() > 0:
                    c_btn.click(force=True)
                    page.wait_for_timeout(3000)
                    continue
                    
            if "about-you" in u:
                age_inp = page.locator('input[name="age"]').first
                if age_inp.count() > 0 and age_inp.is_visible():
                    age_inp.fill("24")
                sub_btn = page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")').first
                if sub_btn.count() > 0:
                    sub_btn.click(force=True)
                    page.wait_for_timeout(3000)

                continue
        page.wait_for_timeout(3000)
        try:
            page.screenshot(path=f"D:/Taadaa/GPM auto/debug_screenshots/canary_{email.split('@')[0]}_after.png")
        except Exception:
            pass
        return _get_clean_session_token()

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
        except sqlite3.DatabaseError:
            if conn:
                try: conn.rollback()
                except sqlite3.Error: pass
            raise
        finally:
            if conn:
                try: conn.close()
                except sqlite3.Error: pass
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
        except (socket.error, TimeoutError, OSError) as e:
            log(f"[IMAP-OTP-WARN] Network/IO error ({type(e).__name__})")
        except Exception as e:
            log(f"[IMAP-OTP-WARN] {type(e).__name__}")
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

            # 2.2b. Tự động lấy mã 10 số S7 và duyệt Google Prompt
            try:
                if "challenge/selection" in cur_url or "selection" in cur_url:
                    sec_opt = page.locator('div[data-challengetype="8"], li:has-text("mã bảo mật"), li:has-text("security code"), div[role="link"]:has-text("mã bảo mật")').first
                    if sec_opt.count() > 0 and sec_opt.is_visible():
                        log(f"[{email}] Chọn phương thức 'Mã bảo mật trên điện thoại'...")
                        sec_opt.click()
                        time.sleep(3)
                        continue
                is_ootp = "challenge/ootp" in cur_url or any(k in page.content().lower() for k in ["mã bảo mật", "security code", "galaxy s7"])
                pin_inp = page.locator('input[name="Pin"], input#security-code-input, input[name="pin"]').first
                if is_ootp and pin_inp.count() > 0 and pin_inp.is_visible() and get_s7_security_code and get_account_for_email:
                    acc_s7 = get_account_for_email(email)
                    if acc_s7 and acc_s7.get("mid") and acc_s7.get("serial"):
                        log(f"[{email}] Lấy mã 10 số S7 (M{acc_s7['mid']:02d})...")
                        s7_code = get_s7_security_code(acc_s7["mid"], acc_s7["serial"], email)
                        if s7_code:
                            pin_inp.fill(s7_code)
                            time.sleep(1)
                            page.keyboard.press("Enter")
                            time.sleep(4)
                            continue
                if ("challenge/dp" in cur_url or "nhấn vào có" in page.content().lower()) and approve_s7_google_prompt and get_account_for_email:
                    acc_s7 = get_account_for_email(email)
                    if acc_s7 and acc_s7.get("mid") and acc_s7.get("serial"):
                        log(f"[{email}] Duyệt Google Prompt trên S7 (M{acc_s7['mid']:02d})...")
                        approve_s7_google_prompt(acc_s7["mid"], acc_s7["serial"], None, target_email=email)
                        time.sleep(4)
                        continue
            except Exception as e:
                log(f"Lỗi phối hợp S7: {e}")

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

# ==================== ARCHITECTURE LAYER 3B: CODEX OAUTH RECOVERY MODULE ====================
def _perform_codex_oauth_unlocked(cdp_addr: str, email: str, creds: dict = None):
    try:
        cb = requests.get(f"{OMNI_API}/api/oauth/codex/start-callback-server", timeout=15).json()
        auth_url = cb.get("authUrl") or (cb.get("data") or {}).get("authUrl")
        if not auth_url:
            return False, f"Không có authUrl từ OmniRoute: {cb}"
    except Exception as e:
        return False, f"Lỗi gọi start-callback-server: {e}"

    acc_info = (creds or {}).get(email.lower(), {})
    password = acc_info.get('password')
    totp_key = acc_info.get('totp')

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}", timeout=15000)
        except Exception as e:
            return False, f"Lỗi CDP: {e}"

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        pages = [pg for pg in context.pages if not pg.url.startswith("chrome-extension://")]
        page = pages[0] if pages else context.new_page()

        def on_req(req):
            url = req.url
            if "1455" in url and ("callback" in url or "code=" in url):
                try:
                    local_url = url.replace("localhost", "127.0.0.1")
                    requests.get(local_url, timeout=5)
                except Exception:
                    pass
        page.on("request", on_req)

        try:
            page.goto(auth_url, timeout=45000, wait_until="domcontentloaded")
        except Exception as e:
            log(f"[{email}] page.goto notice: {e}")
        time.sleep(3)

        start_t = time.time()
        timeout_sec = 90
        conn_id = None

        while time.time() - start_t < timeout_sec:
            for sso_btn in page.locator("button:has-text('Continue with Google'), button:has-text('Tiếp tục với Google'), [data-provider='google']").all():
                try:
                    sso_btn.evaluate("el => el.style.display = 'none'")
                except Exception:
                    pass

            try:
                cur_title = page.title().lower()
                if "kết thúc" in cur_title or "expired" in cur_title:
                    relogin_btn = page.locator("button:has-text('Đăng nhập'), button:has-text('Log in'), a:has-text('Đăng nhập'), a:has-text('Log in')")
                    if relogin_btn.count() > 0 and relogin_btn.first.is_visible():
                        relogin_btn.first.click(force=True)
                        time.sleep(2)
            except Exception:
                pass

            try:
                email_loc = page.locator('input[type="email"], input[name="email"]')
                if email_loc.count() > 0 and email_loc.first.is_visible():
                    cur = email_loc.first.input_value()
                    if cur.lower() != email.lower():
                        email_loc.first.fill(email)
                        time.sleep(0.5)
                    sb = page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue")')
                    if sb.count() > 0 and sb.first.is_visible():
                        sb.first.click()
                        time.sleep(2)
                        continue
            except Exception:
                pass

            try:
                pwd_loc = page.locator('input[type="password"], input[name="password"]')
                if pwd_loc.count() > 0 and pwd_loc.first.is_visible():
                    time.sleep(1.5)
                    pwd_val = pwd_loc.first.input_value()
                    if not pwd_val and password:
                        pwd_loc.first.fill(password)
                        pwd_val = password
                    if pwd_val:
                        sb = page.locator('button[type="submit"], button:has-text("Tiếp tục"), button:has-text("Continue"), button:has-text("Đăng nhập"), button:has-text("Log in")')
                        if sb.count() > 0 and sb.first.is_visible():
                            sb.first.click()
                            time.sleep(2)
                            continue
            except Exception:
                pass

            try:
                cur_url = page.url.lower()
                if "choose-an-account" in cur_url or "welcome back" in cur_url or "chọn tài khoản" in cur_url:
                    acct_btn = page.locator(f"button:has-text('{email}'), [role='button']:has-text('{email}'), a:has-text('{email}')")
                    if acct_btn.count() > 0 and acct_btn.first.is_visible():
                        acct_btn.first.click(force=True)
                        time.sleep(2)
                        continue
            except Exception:
                pass

            try:
                if ("challenge/totp" in page.url.lower() or page.locator('#totpPin:visible').count() > 0) and totp_key:
                    code = pyotp.TOTP(totp_key).now()
                    totp_inp = page.locator('#totpPin, input[type="tel"]').first
                    if totp_inp.count() > 0:
                        totp_inp.fill(code)
                        page.locator('#totpNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
                        time.sleep(4)
                        continue
            except Exception:
                pass

            try:
                for sel in ['button:has-text("Authorize")', 'button:has-text("Cho phép")', 'button:has-text("Allow")', 'button:has-text("Accept")', 'button:has-text("Continue")', 'button:has-text("Tiếp tục")']:
                    btn = page.locator(sel)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        time.sleep(2)
                        break
            except Exception:
                pass

            try:
                cur_url = page.url
                if "1455" in cur_url and ("callback" in cur_url or "code=" in cur_url):
                    local_url = cur_url.replace("localhost", "127.0.0.1")
                    requests.get(local_url, timeout=5)
            except Exception:
                pass

            try:
                poll = requests.post(f"{OMNI_API}/api/oauth/codex/poll-callback", json={}, timeout=10).json()
                is_ok = (poll.get("success") is True or poll.get("status") in ("success", "completed") or "connection" in poll or "connectionId" in poll)
                conn_obj = poll.get("connection") or (poll.get("data") or {}).get("connection") or {}
                found = conn_obj.get("id") or poll.get("connectionId") or poll.get("id")
                if is_ok and found:
                    conn_id = found
                    break
            except Exception:
                pass

            time.sleep(2.5)

        if not conn_id:
            return False, f"Timeout OAuth sau {timeout_sec}s. URL: {page.url[:80]}"

        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('''
                UPDATE provider_connections
                SET is_active=1, test_status='active', last_error=NULL, error_code=NULL, last_error_at=NULL, backoff_level=0, rate_limited_until=NULL, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND provider='codex'
            ''', (conn_id,))
            rows_aff = cur.rowcount
            conn.commit()
            conn.close()
            if rows_aff <= 0:
                return False, f"Connection ID {conn_id} không khớp provider codex"
        except sqlite3.DatabaseError as e:
            log(f"[{email}] DB error updating OAuth: {type(e).__name__}")
            return False, f"Lỗi DB cập nhật OAuth: {type(e).__name__}"
        except Exception as e:
            log(f"[{email}] Error updating DB after OAuth: {type(e).__name__}")
            return False, f"Lỗi cập nhật DB: {type(e).__name__}"

        return True, "Hồi sinh Codex OAuth thành công"


def perform_codex_oauth(cdp_addr: str, email: str, creds: dict = None):
    with CodexOAuth1455Lock():
        return _perform_codex_oauth_unlocked(cdp_addr, email, creds)


def refresh_codex_account_via_gpm(pid: str, email: str, creds: dict = None):
    log(f"Đang mở GPM profile PID {pid} để tự động OAuth Codex cho {email}...")
    try:
        res_start = requests.get(f"{GPM_API}/profiles/start/{pid}?win_scale=0.8", timeout=20).json()
        if not res_start.get('success'):
            return False, f"Start profile fail: {res_start.get('message')}"
        cdp_addr = res_start['data']['remote_debugging_address']
        time.sleep(2)

        ok, msg = perform_codex_oauth(cdp_addr, email, creds)
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
TELEMETRY_PUBLIC_PATH = r"D:\Taadaa\chatgpt_web_pool_telemetry.json"

def categorize_failure(err) -> str:
    """Phân loại lỗi hồi sinh để phục vụ triage & alerting (thứ tự ưu tiên cố định)."""
    err_l = str(err).lower()
    if "phone" in err_l or "số điện thoại" in err_l:
        return "PHONE_CHECKPOINT"
    if "timeout" in err_l:
        return "TIMEOUT"
    if "proxy" in err_l:
        return "PROXY_ERROR"
    if "recaptcha" in err_l:
        return "CAPTCHA_CHALLENGE"
    return "UNKNOWN"

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
        try:
            os.makedirs(os.path.dirname(TELEMETRY_PUBLIC_PATH), exist_ok=True)
            tmp_pub = TELEMETRY_PUBLIC_PATH + f".tmp.{os.getpid()}"
            with open(tmp_pub, "w", encoding="utf-8") as f_pub:
                json.dump(metrics, f_pub, ensure_ascii=False, indent=2)
            if os.path.exists(TELEMETRY_PUBLIC_PATH):
                os.replace(tmp_pub, TELEMETRY_PUBLIC_PATH)
            else:
                os.rename(tmp_pub, TELEMETRY_PUBLIC_PATH)
        except Exception as e_pub:
            log(f"[TELEMETRY-PUBLIC-WARN] Lỗi ghi public telemetry: {e_pub}")
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
    chatgpt_inactive = []
    for c in chatgpt_conns:
        if c.get('isActive') and c.get('testStatus') == 'active':
            continue
        cur_key = c.get('apiKey')
        if cur_key and isinstance(cur_key, str) and cur_key.startswith(('eyJhbG', '__Secure')):
            is_live_ok, _ = test_connection_valid(cur_key)
            if is_live_ok:
                cid = c.get('id')
                try:
                    conn_t = sqlite3.connect(DB_PATH)
                    conn_t.cursor().execute("UPDATE provider_connections SET is_active=1, test_status='active', last_error=NULL, last_error_at=NULL, backoff_level=0 WHERE id=?", (cid,))
                    conn_t.commit()
                    conn_t.close()
                    log(f"  [✓ LIVE TEST VALID] Phục hồi tài khoản {c.get('name')}: Token vẫn còn sống, không cần login lại.")
                    continue
                except Exception:
                    pass
        chatgpt_inactive.append(c)
    
    recovered_chatgpt = []
    failed_chatgpt = []
    
    if chatgpt_inactive:
        log(f"Phát hiện {len(chatgpt_inactive)} tài khoản ChatGPT-Web cần hồi sinh (chạy song song 5 workers)...")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def _worker_task(c_info):
            cname = c_info.get('name', '')
            cid = c_info.get('id')
            import re
            m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', cname)
            if not m:
                return None, False, "No email match"
            email = m.group(1).lower()
            prof = get_unambiguous_gpm_profile(gpm_map, email)
            if not prof:
                return email, False, "AMBIGUOUS_GPM_PROFILE" if len(gpm_map.get(email, [])) > 1 else "Không thấy profile GPM"
            pid = prof['id']
            ok, msg = refresh_chatgpt_account_via_gpm(pid, cid, email, creds)
            return email, ok, msg

        with ThreadPoolExecutor(max_workers=5, thread_name_prefix="ChatGPTHealer") as executor:
            future_map = {executor.submit(_worker_task, c): c for c in chatgpt_inactive}
            for fut in as_completed(future_map):
                try:
                    em, ok, msg = fut.result()
                    if em:
                        if ok:
                            recovered_chatgpt.append(em)
                            log(f"  [✓ RECOVERED] {em}")
                        else:
                            failed_chatgpt.append((em, msg))
                            log(f"  [✗ FAILED] {em}: {msg}")
                except Exception as ex:
                    log(f"Worker exception: {ex}")
                
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
            prof = get_unambiguous_gpm_profile(gpm_map, email)
            if prof:
                pid = prof['id']
                ok, msg = refresh_antigravity_account_via_gpm(pid, email, prof, creds)
                if ok:
                    recovered_ag.append(email)
                else:
                    failed_ag.append((email, msg))
            else:
                failed_ag.append((email, "AMBIGUOUS_GPM_PROFILE" if len(gpm_map.get(email, [])) > 1 else "Không thấy profile GPM"))

    # 3. Quét Codex OAuth: Tự động hồi sinh các tài khoản Codex bị lỗi / token invalid
    codex_conns = get_connections_by_provider('codex')
    codex_broken = []
    for c in codex_conns:
        cname = (c.get('name') or c.get('id', '')).lower()
        if 'auth.json' in cname or '@hotmail.com' in cname:
            continue
        # Kiểm tra nếu connection không active hoặc testStatus != 'active'
        if not (c.get('isActive') and c.get('testStatus') == 'active'):
            cid = c.get('id')
            reason = codex_oauth_invalid_reason(c)
            if not reason:
                try:
                    r_test = requests.post(f"{OMNI_API}/api/providers/{cid}/test", json={}, timeout=5).json()
                    if r_test.get('valid') is False and r_test.get('statusCode') == 401:
                        reason = "401_token_revoked"
                except Exception:
                    pass
            if reason:
                codex_broken.append((c, reason))

    recovered_codex = []
    failed_codex = []
    disabled_codex = []
    if codex_broken:
        log(f"Phát hiện {len(codex_broken)} tài khoản Codex cần OAuth hồi sinh...")
        for c, reason in codex_broken:
            cname = c.get('name') or c.get('id', 'unknown')
            import re
            m = re.search(r'([a-zA-Z0-9_.+-]+@gmail\.com)', cname.lower())
            if not m:
                failed_codex.append((cname, f"NO_GMAIL_EXTRACTED: {reason}"))
                if disable_codex_connection(c, reason):
                    disabled_codex.append((cname, reason))
                continue
            email = m.group(1).lower()
            prof = get_unambiguous_gpm_profile(gpm_map, email)
            if prof:
                pid = prof['id']
                ok, msg = refresh_codex_account_via_gpm(pid, email, creds)
                if ok:
                    recovered_codex.append(email)
                else:
                    failed_codex.append((email, msg))
                    if disable_codex_connection(c, reason):
                        disabled_codex.append((email, reason))
            else:
                failed_codex.append((email, "AMBIGUOUS_GPM_PROFILE" if len(gpm_map.get(email, [])) > 1 else "Không thấy profile GPM"))
                if disable_codex_connection(c, reason):
                    disabled_codex.append((email, reason))


    chatgpt_after = get_connections_by_provider('chatgpt-web')
    chatgpt_active_cnt = sum(1 for c in chatgpt_after if c.get('isActive') and c.get('testStatus') == 'active')
    
    ag_after = get_connections_by_provider('antigravity')
    ag_active_cnt = sum(1 for c in ag_after if c.get('isActive') and c.get('testStatus') == 'active')

    codex_after = get_connections_by_provider('codex')
    codex_active_cnt = sum(1 for c in codex_after if c.get('isActive') and c.get('testStatus') == 'active')
    
    all_failed = failed_chatgpt + failed_ag + failed_codex
    if not recovered_chatgpt and not recovered_ag and not all_failed and not disabled_codex:
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
    if recovered_codex:
        report_lines.append(f"• Đã hồi sinh Codex ({len(recovered_codex)} acc): {', '.join([a.split('@')[0] for a in recovered_codex])}")
    if disabled_codex:
        report_lines.append(f"• Đã disable Codex OAuth invalid ({len(disabled_codex)} acc):")
        for account, reason in disabled_codex[:5]:
            report_lines.append(f"  - `{account}`: {reason}")
        if len(disabled_codex) > 5:
            report_lines.append(f"  - *...và {len(disabled_codex) - 5} tài khoản khác*")
        
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
        categorized_failures.append({"account": a, "category": categorize_failure(err_str), "error": err_str[:100]})
    failure_categories = {}
    for f_item in categorized_failures:
        failure_categories[f_item["category"]] = failure_categories.get(f_item["category"], 0) + 1

    scan_ts = datetime.now(timezone.utc).isoformat()
    telemetry_data = {
        "timestamp": scan_ts,
        "last_scan": scan_ts,
        "chatgpt_web": {"active": chatgpt_active_cnt, "total": len(chatgpt_after)},
        "antigravity": {"active": ag_active_cnt, "total": len(ag_after)},
        "codex": {"active": codex_active_cnt, "total": len(codex_after)},
        "recovered_chatgpt": recovered_chatgpt,
        "recovered_ag": recovered_ag,
        "recovered_codex": recovered_codex,
        "disabled_codex": [d[0] if isinstance(d, (tuple, list)) else str(d) for d in disabled_codex],
        "total_failures": len(all_failed),
        "failures": categorized_failures,
        "failure_categories": failure_categories
    }
    save_telemetry_metrics(telemetry_data)

    report_msg = "\n".join(report_lines)
    print(report_msg)

if __name__ == '__main__':
    main()
