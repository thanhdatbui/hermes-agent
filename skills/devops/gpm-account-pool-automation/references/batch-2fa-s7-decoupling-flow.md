# Batch 2FA Google Authenticator Activation & S7 Decoupling Workflow

## 1. Mục Đích & Nguyên Lý Tách Biệt S7
Khi tài khoản Gmail đăng nhập lần đầu trên thiết bị Android Samsung Galaxy S7 (Farm), Google đánh dấu S7 là thiết bị tin cậy bậc 1 và mặc định đẩy thông báo (Google Prompt / chọn số) về S7 khi đăng nhập trên trình duyệt mới. Nếu máy S7 bị hỏng hoặc bận cron, phiên đăng nhập trên trình duyệt sẽ bị nghẽn.

**Giải pháp:**
1. Lấy mã bảo mật 10 số (Security Code) từ S7 qua ADB để vượt qua lần đăng nhập đầu tiên trên GPM Browser.
2. Ngay sau khi vào được, điều hướng tới `https://myaccount.google.com/signinoptions/twosv`.
3. Bật 2-Step Verification → Thêm Google Authenticator → Trích xuất chuỗi **Base32 Secret Key (32 ký tự)** → Dùng `pyotp.TOTP(secret).now()` xác nhận kích hoạt thành công với Google.
4. Lưu chuỗi Secret Key vào file Excel tổng (`master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`).
5. **Kết quả:** Các lần đăng nhập sau hoàn toàn độc lập với máy S7, chỉ cần đọc Secret Key từ Excel sinh mã OTP 6 số.

---

## 2. Quy Trình ADB Lấy Mã Bảo Mật 10 Số Trên Samsung S7
```python
def get_s7_security_code(machine_id, serial, target_email):
    atx_port = 17000 + machine_id
    subprocess.run([ADB_EXE, "-s", serial, "forward", f"tcp:{atx_port}", "tcp:7912"], capture_output=True)
    
    # 1. Wake & unlock
    subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "26"])
    subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "500", "1500", "500", "500"])
    
    # 2. Open Settings -> Scroll to Google -> Tap Google
    subprocess.run([ADB_EXE, "-s", serial, "shell", "am", "start", "-a", "android.settings.SETTINGS"])
    # (Swipe & dump UI via atx-agent port 17000 + machine_id)
    
    # 3. Switch to target_email in Google account list
    # 4. Tap "Quản lý Tài khoản Google" (Manage your Google Account)
    # 5. Tap "Bảo mật và đăng nhập" / "Bảo mật" -> Tap "Mã bảo mật" (Security code)
    # 6. Extract 10-digit code from screen hierarchy
```

---

## 3. Quy Trình Kích Hoạt 2FA Authenticator Trên Playwright — **URL TRỰC TIẾP (FIX 2026-09-03)**

**Vấn đề cũ:** Page `https://myaccount.google.com/signinoptions/twosv` có overlay shadow DOM (`.uW2Fw-Sx9Kwc`, `.uW2Fw-IE5DDf`) chặn click vào nút "Authenticator" → Playwright timeout 30s.

**Giải pháp chuẩn (đã verify):** Dùng URL trực tiếp **`https://myaccount.google.com/two-step-verification/authenticator`** → bỏ qua hoàn toàn page chính và overlay.

```python
# 1. Open Authenticator DIRECT URL (bypasses shadow DOM overlay)
page.goto("https://myaccount.google.com/two-step-verification/authenticator", wait_until="domcontentloaded", timeout=45000)
time.sleep(2)

# 2. Click "Thiết lập" / "Set up" (inside page, not dialog yet)
page.locator('button:has-text("Thiết lập"), button:has-text("Set up")').first.click(force=True)
time.sleep(3)

# 3. Wait for QR dialog to load, then click "Không thể quét mã?" / "Can't scan it?"
cant_scan = page.locator('div[role="dialog"] button:has-text("quét"), div[role="dialog"] button:has-text("scan"), div[role="dialog"] button:has-text("Can")')
cant_scan.wait_for(state="visible", timeout=15000)
cant_scan.first.click(force=True)
time.sleep(2)

# 4. Extract 32-char Base32 Secret Key
# Format displayed: "fuyk 3a5v vx37 cenh mgtg dq7s epme h3hh" (8 groups of 4, space-separated)
dialog = page.locator('div[role="dialog"]')
dialog_text = dialog.inner_text()

secret_key = None
# First try: 32 contiguous alphanumeric
for line in dialog_text.splitlines():
    cleaned = line.strip().replace(" ", "")
    if len(cleaned) == 32 and cleaned.isalnum():
        secret_key = cleaned.upper()
        break

# Second try: 8 groups of 4 space-separated (the actual format Google shows)
if not secret_key:
    match = re.search(r"([a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4})", dialog_text)
    if match:
        secret_key = match.group(1).replace(" ", "").upper()

# 5. Click "Tiếp theo" / "Next"
for b in dialog.locator("button").all():
    if b.is_visible() and any(w in b.inner_text().lower() for w in ["next", "tiếp"]):
        b.click()
        break
time.sleep(2)

# 6. Generate TOTP code & verify
totp_code = pyotp.TOTP(secret_key).now()
code_input = dialog.locator('input[type="text"], input[type="tel"]')
if code_input.count() > 0 and code_input.first.is_visible():
    code_input.first.fill(totp_code)
    time.sleep(1)

for b in dialog.locator("button").all():
    if b.is_visible() and any(w in b.inner_text().lower() for w in ["verify", "xác minh", "done", "xong"]):
        b.click()
        break
time.sleep(4)
```

---

## 4. Quy Chuẩn Bảng Excel Tổng (`master_gmail_manager.xlsx`)
Gồm 15 cột chuẩn hóa:
1. `STT`
2. `Email`
3. `Password`
4. `Recovery_Email`
5. `2FA_Secret`
6. `SDT`
7. `Trạng Thái` (`Live` / `2FA_ENABLED`)
8. `Số Máy Farm` (`Máy 02`, `Máy 42`, `Admin_Port_10008`...)
9. `Model Điện Thoại` (`Samsung Galaxy S7` / `GPM Browser / PC`)
10. `Serial Thiết Bị (Device ID)` (`9885e6303951513337`, `ce06160692e07d0404`...)
11. `Proxy Đang Dùng` (`http://192.168.110.2:20002 (test.taadaa.click:5102)`)
12. `Tên Profile GPM` (`02 - duongthanhha270820032708@gmail.com`)
13. `Nguồn` (`clean_v2` / `gmail-dat`)
14. `Ghi Chú`
15. `Cập Nhật`

---

## 5. Kỷ Luật Worker & Đóng Profile (BẮT BUỘC)
- **Max Workers:** 10 luồng song song (`ThreadPoolExecutor(max_workers=10)`).
- **Khối `finally:` bắt buộc:**
  ```python
  finally:
      if context:
          context.close()
      if playwright:
          playwright.stop()
  ```
- Dù Success hay Error/Timeout, browser profile phải lập tức đóng lại, không để lại tiến trình Chrome mồ côi trên Taskbar/RAM.

---

## 6. Pitfalls & Fixes Learned (2026-09-03)

| Issue | Root Cause | Fix |
|-------|------------|-----|
| `Locator.click: Timeout 30000ms exceeded` on Authenticator option | Shadow DOM overlay (`.uW2Fw-Sx9Kwc`, `.uW2Fw-IE5DDf`) intercepts pointer events | Use **direct URL** `https://myaccount.google.com/two-step-verification/authenticator` instead of navigating from `twosv` page |
| Click intercepted even with `.last` selector | Overlay covers entire viewport | Add `force=True` to `click(force=True)` for all buttons inside shadow DOM affected areas |
| "Không thể quét mã?" button not found | Button only appears AFTER QR code finishes loading | Wait explicitly: `cant_scan.wait_for(state="visible", timeout=15000)` |
| Secret key not extracted by 32-char regex | Google displays key as **8 groups of 4 chars with spaces**: `fuyk 3a5v vx37 cenh mgtg dq7s epme h3hh` | Use fallback regex matching space-separated groups pattern |
| Page timeout navigating to `twosv` | 4G proxy (Singbox/MikroTik) + `wait_until="load"` waits for all resources | Use `wait_until="domcontentloaded"` for all Playwright navigations |
| S7 Security Code fetch fails | ADB UI hierarchy dump misses "Google" / "Bảo mật" text due to scroll position | Robust wake/unlock + scroll loop + multiple UI dump retries before tapping |

---

## 7. Production Batch Script
Full production script at: `D:/Taadaa/GPM auto/scripts/run_batch_2fa_kibe_pool.py`
- Implements all fixes above
- 10 concurrent workers
- Thread-safe Excel writes
- Detailed logging to `D:\Taadaa\GPM auto\logs\batch_2fa_run.log`
- Failure report at `D:\Taadaa\GPM auto\logs\batch_failures.json`