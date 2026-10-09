# Full Pipeline: 2FA Google Authenticator → Hot Session OAuth → Combo Append
_Captured 2026-09-08 — M39 (Port 5101) và M60 (Port 5126)_

## Mục đích
Khi user nói **"bật 2FA + nạp OAuth + nạp vào combo ag-gemini-pool-3"** cho máy GPM farm,
chạy 3 bước nối tiếp trong **cùng 1 Playwright `page` object (hot session)** — không cần re-login:

```
GPM Start Profile → CDP connect → [bật 2FA Authenticator] → hot_session_oauth() → append_connections()
```

## Script pattern chuẩn

File recommended: `D:\Taadaa\GPM auto\scripts\run_full_pipeline_2fa_and_oauth.py`

```python
import sys, os, time, re, json, logging, datetime
import pyotp, openpyxl, requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
from hot_session_oauth import trigger_hot_session_oauth
from append_to_combo_pool3 import append_connections

GPM_API_BASE = "http://127.0.0.1:19995/api/v3"
MASTER_EXCEL  = r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx"
CLEAN_V2_EXCEL = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
ADB_EXE = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"

TARGETS = [
    {
        "mid": 39,
        "email": "tachau17042004@gmail.com",
        "pwd": ["Tachau17042004@Ks"],
        "totp_secret": None,         # None = cần bật 2FA; "ABC..." = đã có sẵn
        "serial": "ce0117113818c4d30c",
        "port": 5101,
        "gpm_profile_id": "???",     # Phải lookup DB trước — xem Pitfall 1
        "need_2fa": True,
    },
    {
        "mid": 60,
        "email": "crystalwwilsonlypp1@gmail.com",
        "pwd": ["Hnpixpbvnfun"],
        "totp_secret": None,
        "serial": "ce09160963abd20e02",
        "port": 5126,
        "gpm_profile_id": "dbd36ade-f94e-4641-84d4-243c77032d9f",
        "need_2fa": True,
    },
]

def find_first_visible(container, selectors):
    for sel in selectors:
        try:
            loc = container.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                return loc.first
        except Exception:
            pass
    return None

def save_secret_to_excels(email, secret_key, final_pwd=None):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    masked = secret_key[:6] + "..." if secret_key and len(secret_key) >= 6 else "[EMPTY]"
    # master_gmail_manager.xlsx — sheets Master_All + Kibe_Farm_S7
    try:
        wb = openpyxl.load_workbook(MASTER_EXCEL)
        for sheet_name in ["Master_All", "Kibe_Farm_S7"]:
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                for r in range(2, ws.max_row + 1):
                    em = str(ws.cell(r, 2).value or "").strip().lower()
                    if em == email.lower():
                        ws.cell(r, 5, secret_key)
                        ws.cell(r, 7, "LIVE")
                        if final_pwd:
                            ws.cell(r, 3, final_pwd)
                        if ws.max_column >= 15:
                            ws.cell(r, 15, now_str)
        wb.save(MASTER_EXCEL); wb.close()
    except Exception as e:
        logging.error(f"[EXCEL MASTER ERROR] {email}: {e}")
    # gmail_clean_v2.xlsx
    try:
        wb2 = openpyxl.load_workbook(CLEAN_V2_EXCEL)
        ws2 = wb2.active
        for r in range(2, ws2.max_row + 1):
            em = str(ws2.cell(r, 2).value or "").strip().lower()
            if em == email.lower():
                ws2.cell(r, 4, secret_key)
                if final_pwd:
                    ws2.cell(r, 3, final_pwd)
        wb2.save(CLEAN_V2_EXCEL); wb2.close()
    except Exception as e:
        logging.error(f"[EXCEL CLEAN ERROR] {email}: {e}")

def handle_challenges(page, target):
    """Vượt password/S7-security-code re-auth challenges."""
    pwds = target["pwd"] if isinstance(target["pwd"], list) else [target["pwd"]]
    for pwd in pwds:
        if "challenge/pwd" in page.url or page.locator('input[type="password"]').count() > 0:
            try:
                pw_box = page.locator('input[type="password"]').first
                pw_box.wait_for(state="visible", timeout=8000)
                pw_box.fill(pwd)
                nxt = find_first_visible(page, ['button:has-text("Next")', 'button:has-text("Tiếp theo")', '#passwordNext'])
                if nxt: nxt.click()
                else: page.keyboard.press("Enter")
                for _ in range(25):
                    time.sleep(1)
                    if "challenge/pwd" not in page.url: break
                time.sleep(3)
                if "challenge/pwd" not in page.url:
                    target["_correct_pwd"] = pwd
                    break
            except Exception: pass

def do_2fa_setup(page, target):
    """Bật Google Authenticator và trả về secret_key (32 ký tự)."""
    email = target["email"]
    # Vào trang 2SV tổng
    page.goto("https://myaccount.google.com/signinoptions/twosv", wait_until="domcontentloaded", timeout=45000)
    time.sleep(3); handle_challenges(page, target)
    # Vào trang Authenticator
    page.goto("https://myaccount.google.com/two-step-verification/authenticator", wait_until="domcontentloaded", timeout=45000)
    time.sleep(3); handle_challenges(page, target)
    # Dismiss popups
    for _ in range(2):
        d = find_first_visible(page, ['button:has-text("Bỏ qua")', 'button:has-text("Cancel")', 'button:has-text("Không")'])
        if d: d.click(); time.sleep(1)
    # Bấm Thiết lập hoặc Thay đổi
    btn = find_first_visible(page, [
        'button:has-text("Change authenticator")', 'button:has-text("Thay đổi ứng dụng")',
        'button:has-text("Set up authenticator")', 'button:has-text("Thiết lập ứng dụng")',
        'button:has-text("Thiết lập")', 'button:has-text("Set up")',
    ])
    if btn: btn.click(); time.sleep(3)
    # Bấm "Không thể quét mã?"
    cant_scan = find_first_visible(page, [
        'button:has-text("scan")', 'button:has-text("quét")',
        'text=Can\'t scan', 'text=Không thể quét',
    ])
    if cant_scan: cant_scan.click(); time.sleep(2)
    # Đọc secret key
    dialog = page.locator('div[role="dialog"]')
    dialog_text = dialog.inner_text() if dialog.count() > 0 else page.inner_text("body")
    secret_key = None
    m = re.search(r"([a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4})", dialog_text)
    if m:
        secret_key = m.group(1).replace(" ", "").upper()
    else:
        for line in dialog_text.splitlines():
            c = line.strip().replace(" ", "")
            if len(c) == 32 and c.isalnum(): secret_key = c.upper(); break
    if not secret_key:
        raise RuntimeError(f"[{email}] Không trích được Secret Key 32 ký tự")
    # Bấm Next trong dialog
    for b in dialog.locator("button, [role='button']").all():
        if b.is_visible() and any(w in b.inner_text().lower() for w in ["next", "tiếp"]):
            b.click(); break
    time.sleep(2)
    # Điền TOTP
    totp_code = pyotp.TOTP(secret_key).now()
    code_box = dialog.locator('input:visible, input[type="text"], input[placeholder*="code"], input[placeholder*="mã"]').first
    code_box.fill(totp_code); time.sleep(1)
    for b in dialog.locator("button, [role='button']").all():
        if b.is_visible() and any(w in b.inner_text().lower() for w in ["verify", "xác minh", "done", "xong"]):
            b.click(); break
    time.sleep(4)
    return secret_key

def process_one(target):
    mid = target["mid"]; email = target["email"]; port = target["port"]
    pid = target["gpm_profile_id"]; need_2fa = target.get("need_2fa", False)
    result = {"mid": mid, "email": email, "status": "FAIL", "secret": None, "conn_id": None, "reason": ""}
    browser = None
    try:
        # 1. Start GPM Profile
        resp = requests.get(f"{GPM_API_BASE}/profiles/start/{pid}", timeout=30).json()
        if not resp.get("success"):
            result["reason"] = f"GPM start failed: {resp.get('message')}"; return result
        cdp_addr = resp.get("data", {}).get("remote_debugging_address")
        if not cdp_addr:
            result["reason"] = "No CDP address"; return result
        logging.info(f"[M{mid:02d}] CDP={cdp_addr}, sleeping 8s...")
        time.sleep(8)

        with sync_playwright() as pw:
            for _ in range(5):
                try:
                    browser = pw.chromium.connect_over_cdp(f"http://{cdp_addr}", timeout=12000); break
                except Exception: time.sleep(2.5)
            if not browser:
                result["reason"] = "CDP connect failed after 5 attempts"; return result

            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            regular = [p for p in ctx.pages if not p.url.startswith("chrome-extension://")]
            page = regular[0] if regular else ctx.new_page()
            page.set_default_timeout(35000)

            # 2. Bật 2FA nếu cần
            if need_2fa:
                secret = do_2fa_setup(page, target)
                save_secret_to_excels(email, secret, target.get("_correct_pwd"))
                result["secret"] = secret
                logging.info(f"[M{mid:02d}] 2FA bật thành công, secret lưu Excel. Secret: {secret[:6]}...")

            # 3. Hot Session OAuth (cùng page, không đóng browser)
            oauth_result = trigger_hot_session_oauth(page, email, mid, port, f"M{mid:02d}")
            if oauth_result.get("status") == "SUCCESS":
                result["conn_id"] = oauth_result.get("cid")
                result["status"] = "SUCCESS"
                logging.info(f"[M{mid:02d}] OAuth + combo append OK! CID={result['conn_id']}")
            else:
                result["reason"] = f"OAuth failed: {oauth_result.get('reason')}"
    except Exception as e:
        result["reason"] = str(e); logging.error(f"[M{mid:02d}] Exception: {e}", exc_info=True)
    finally:
        if browser:
            try: browser.close()
            except Exception: pass
        try: requests.get(f"{GPM_API_BASE}/profiles/stop/{pid}", timeout=15)
        except Exception: pass
    return result

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results = [process_one(t) for t in TARGETS]
    for r in results:
        secret_mask = r["secret"][:6] + "..." if r["secret"] else "NONE"
        logging.info(f"M{r['mid']:02d} | {r['email']} | {r['status']} | Secret={secret_mask} | CID={r['conn_id']}")

if __name__ == "__main__": main()
```

## GPM Profile ID Lookup — Chuẩn bị BẮT BUỘC trước khi viết script

```python
import sqlite3
DB = r'C:/Users/Kibe/AppData/Local/Programs/GPMLogin/profile/profile_data.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Tìm theo email (reliable nhất)
cur.execute("SELECT name,ProfilePath,Id FROM Profiles WHERE lower(Name) LIKE ?", ('%crystalwwilsonlypp1%',))
# Hoặc theo port
cur.execute("SELECT name,ProfilePath,Id FROM Profiles WHERE lower(Name) LIKE ?", ('%5126%',))
# Hoặc theo số máy (pattern chuẩn: "60 - email@... - 5NNN")
cur.execute("SELECT name,ProfilePath,Id FROM Profiles WHERE Name LIKE ?", ('60 -%',))
```

**Kết quả đã xác nhận:**
- M60 `crystalwwilsonlypp1@gmail.com` → ProfileId = `dbd36ade-f94e-4641-84d4-243c77032d9f`

## Pitfalls

### PITFALL 1 — Profile M39 không tìm thấy theo số máy
Pattern `"39 - tachau%"` trả về 0 kết quả nếu profile được tạo không theo chuẩn `NN - email - port`.
Khi đó: search theo email (`LIKE '%tachau17042004%'`) hoặc cần tạo mới profile qua GPM API trước.

### PITFALL 2 — Tool calls cạn do đọc scripts tuần tự
Pattern thường thất bại: đọc từng file script tuần tự qua nhiều turn → hết iterations.

**Giải pháp:** Batch tất cả `read_file` cần thiết vào **1 turn đầu tiên song song**:
- `hot_session_oauth.py`
- `append_to_combo_pool3.py`
- `run_2fa_9profiles.py` (pattern trích secret key + `save_secret_to_excels`)
- DB lookup query

Rồi viết script NGAY trong turn tiếp theo. Không đọc từng file riêng.

### PITFALL 3 — need_2fa=False khi account đã có totp_secret
Nếu máy đã có secret 32 ký tự trong Excel → `need_2fa=False`, bỏ qua bước setup 2FA.
Chỉ cần `trigger_hot_session_oauth()` trong hot session.

### PITFALL 4 — Đừng đóng browser giữa 2FA và OAuth
`trigger_hot_session_oauth(page, ...)` phải nhận **cùng `page` object** đang đã logged-in Google.
Nếu đóng browser sau 2FA rồi mở lại → Google có thể yêu cầu re-auth → fail OAuth.

### PITFALL 5 — Secret key có space trong dialog text
Pattern trích thường là `"xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx"` (8 nhóm 4 ký tự).
Dùng `m.group(1).replace(" ", "").upper()` → 32 ký tự liền.
Fallback: duyệt từng line tìm chuỗi 32 ký tự `isalnum()`.

## Kết quả session 2026-09-08
- M60 profile ID đã xác nhận: `dbd36ade-f94e-4641-84d4-243c77032d9f`
- M39 profile chưa xác định được — cần lookup thêm hoặc tạo profile mới
- Script chưa được chạy (hết tool calls); cần khởi lại session với batch tool calls ngay từ đầu
