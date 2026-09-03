# Google Prompt (Galaxy S7 Push) & Recovery Email Hierarchy

## 1. Cơ Chế Google Prompt Trên Thiết Bị Tin Cậy Bậc 1 (Trusted Device)
Khi một tài khoản Gmail đã được đăng nhập vào CH Play / Google Play Services trên điện thoại Android thật (Galaxy S7 trong farm):
- Google mặc định coi thiết bị đó là **Thiết bị tin cậy bậc 1**.
- Mỗi khi đăng nhập trên trình duyệt mới (GPM / Playwright), Google sẽ tự động đẩy thông báo xác nhận: *"Kiểm tra Galaxy S7 của bạn ... Nhấn vào số XX"*.
- **Khi S7 đang bận (cron nuôi TikTok đang chạy foreground):** Thông báo Google Prompt không pop up kịp → phiên đăng nhập bị hủy. **Không nên dùng S7 Prompt khi cron đang chạy.**

---

## 2. Luồng SECURITY CODE từ Máy S7 — PHƯƠNG ÁN ƯU TIÊN (Đã Chứng Minh Hoạt Động 2026-09-03)

### Lý do dùng Security Code thay vì Google Prompt:
- Google Prompt cần màn hình S7 không bị ứng dụng khác chiếm foreground.
- Security Code không yêu cầu điều đó — máy S7 có thể đang chạy TikTok, chỉ cần lấy code từ Settings.

### Cơ chế:
1. **Trên S7:** Vào `Cài đặt → Google → Tất cả dịch vụ (tab) → Bảo mật → Mã bảo mật`.
2. S7 sẽ hiện 2 mã số 10 chữ số, có hiệu lực **15 phút** kể từ thời điểm mở trang.
3. **Trên GPM Chrome:** Sau khi nhập mật khẩu, trang challenge hiện các options. Click vào `li` có text `"Sử dụng điện thoại hoặc máy tính bảng của bạn để nhận mã bảo mật (ngay cả khi không có kết nối mạng)"`.
4. Trang tiếp theo (`challenge/selection` với `lid=2`) hướng dẫn: mở Settings S7 → Bảo mật → Mã bảo mật → nhập mã.
5. Điền mã vào input trên Chrome → Tiếp theo → **Google xác nhận thành công.**

### Flow tự động hoàn chỉnh (ADB + Playwright):

```python
import subprocess, time, re, requests, xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"

def get_s7_security_codes(serial, machine_num):
    """Lấy 2 Security Code từ máy S7 qua ADB + atx-agent."""
    atx_port = 17000 + int(machine_num)
    subprocess.run([ADB, "-s", serial, "forward", f"tcp:{atx_port}", "tcp:7912"])
    time.sleep(1)

    # 1. Mở Settings → Google
    subprocess.run([ADB, "-s", serial, "shell", "am", "start", "-a", "android.settings.SYNC_SETTINGS"])
    time.sleep(2)

    # 2. Scroll xuống và click "Google" item
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if node.attrib.get("text", "") == "Google":
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 3. Click vào tên tài khoản Gmail mục tiêu
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        text = node.attrib.get("text", "")
        if "@gmail.com" in text:
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 4. Click "Tất cả dịch vụ" tab rồi scroll tới "Bảo mật" → "Mã bảo mật"
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if "Tất cả dịch vụ" in node.attrib.get("text", ""):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 5. Scroll để tìm "Bảo mật và đăng nhập" rồi vào đó
    subprocess.run([ADB, "-s", serial, "shell", "input", "swipe", "500", "1600", "500", "600"])
    time.sleep(2)
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if "Bảo mật và đăng nhập" in node.attrib.get("text", ""):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(3)
                break

    # 6. Scroll xuống và click "Mã bảo mật"
    subprocess.run([ADB, "-s", serial, "shell", "input", "swipe", "500", "1600", "500", "600"])
    time.sleep(2)
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    for node in root.iter("node"):
        if "Mã bảo mật" in node.attrib.get("text", ""):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
            if m:
                x = (int(m.group(1)) + int(m.group(3))) // 2
                y = (int(m.group(2)) + int(m.group(4))) // 2
                subprocess.run([ADB, "-s", serial, "shell", "input", "tap", str(x), str(y)])
                time.sleep(4)
                break

    # 7. Đọc các mã
    r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
    root = ET.fromstring(r.json().get("result", ""))
    codes = []
    for node in root.iter("node"):
        text = node.attrib.get("text", "").replace("\u202d", "").replace(" ", "")
        if re.match(r"^\d{10}$", text):
            codes.append(text)
    return codes  # [code1, code2]
```

---

## 3. Tự Động Kích Hoạt 2FA Google Authenticator & Tách Khỏi Sự Phụ Thuộc Máy S7 (Verified 100% 2026-09-03)

Sau khi đăng nhập vào GPM thành công bằng Security Code, **BẮT BUỘC** kích hoạt ngay 2FA Authenticator TOTP trên Chrome để tách vĩnh viễn tài khoản khỏi S7.

### Flow Kích Hoạt Tự Động:
1. Mở trang: `https://myaccount.google.com/signinoptions/twosv`.
2. Nếu Google yêu cầu Re-auth: Bấm *"Thử cách khác"* $\rightarrow$ Chọn *"Mã bảo mật"* $\rightarrow$ Điền mã 10 số từ S7.
3. Bấm **"Turn on 2-Step Verification"** (hoặc Bật).
4. Chọn mục **"Authenticator app"** / **"Add authenticator app"**.
5. Bấm nút **"Set up authenticator"**.
6. Bấm **"Can't scan it?"** (Không thể quét mã?).
7. Trích xuất chuỗi **Secret Key (Base32)** gồm 32 ký tự (ví dụ: `5pct jcg3 6jqb ziax ogdq ftmz 2nfm m3os` $\rightarrow$ `5PCTJCG36JQBIAXOGDQFTMZ2NFMM3OS`).
8. Dùng `pyotp.TOTP(secret_key).now()` sinh mã 6 số.
9. Bấm nút visible **"Next"** trong dialog $\rightarrow$ Điền mã 6 số $\rightarrow$ Bấm nút visible **"Verify"** / **"Done"**.
10. Lưu Secret Key vào file `master_gmail_manager.xlsx` (cột `2FA_Secret`) và `gmail_clean_v2.xlsx` (cột `2fa`).

### Script Mẫu Chuẩn:

```python
import time, re, pyotp, openpyxl
from playwright.sync_api import sync_playwright

def setup_google_authenticator_2fa(page, email, master_xlsx_path, clean_v2_path):
    """Kích hoạt Google Authenticator 2FA và lưu Secret Key vào Excel."""
    page.goto("https://myaccount.google.com/signinoptions/twosv", timeout=15000)
    time.sleep(3)

    # 1. Click Add authenticator app
    auth_opt = page.locator('div:has-text("Authenticator"), div:has-text("Add authenticator app"), div:has-text("Thêm ứng dụng Authenticator")').last
    if auth_opt.count() > 0:
        auth_opt.click()
        time.sleep(3)

    # 2. Click Set up authenticator
    setup_btn = page.locator('button:has-text("Set up authenticator"), button:has-text("Thiết lập ứng dụng xác thực"), button:has-text("Thiết lập")')
    if setup_btn.count() > 0:
        setup_btn.first.click()
        time.sleep(3)

    # 3. Click "Can't scan it?"
    cant_scan = page.locator('button:has-text("scan"), button:has-text("quét")')
    if cant_scan.count() > 0:
        cant_scan.first.click()
        time.sleep(2)

    dialog = page.locator('div[role="dialog"]')
    dialog_text = dialog.inner_text() if dialog.count() > 0 else page.inner_text("body")

    # Extract 32-char Base32 secret key
    secret_key = None
    for line in dialog_text.splitlines():
        cleaned = line.strip().replace(" ", "")
        if len(cleaned) == 32 and cleaned.isalnum():
            secret_key = cleaned.upper()
            break

    if not secret_key:
        match = re.search(r'([a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4}\s+[a-zA-Z0-9]{4})', dialog_text)
        if match:
            secret_key = match.group(1).replace(" ", "").upper()

    if not secret_key:
        return False, "Could not extract Secret Key"

    # Click visible Next button
    for b in dialog.locator("button").all():
        if b.is_visible() and any(w in b.inner_text().lower() for w in ["next", "tiếp"]):
            b.click()
            break
    time.sleep(2)

    # Generate TOTP code
    totp_code = pyotp.TOTP(secret_key).now()

    # Fill code
    code_input = dialog.locator('input[type="text"], input[type="tel"]')
    if code_input.count() > 0 and code_input.first.is_visible():
        code_input.first.fill(totp_code)
        time.sleep(1)

    # Click visible Verify / Done button
    for b in dialog.locator("button").all():
        if b.is_visible() and any(w in b.inner_text().lower() for w in ["verify", "xác minh", "done", "xong"]):
            b.click()
            break
    time.sleep(4)

    # Save to master_gmail_manager.xlsx
    wb = openpyxl.load_workbook(master_xlsx_path)
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for r in range(2, ws.max_row + 1):
            em = ws.cell(r, 2).value
            if em and email.lower() in str(em).lower():
                for c in range(1, ws.max_column + 1):
                    head = str(ws.cell(1, c).value or "").lower()
                    if "2fa" in head or "secret" in head:
                        ws.cell(r, c, secret_key)
    wb.save(master_xlsx_path)

    # Save to gmail_clean_v2.xlsx
    wb_clean = openpyxl.load_workbook(clean_v2_path)
    ws_clean = wb_clean.active
    for r in range(2, ws_clean.max_row + 1):
        em = ws_clean.cell(r, 2).value
        if em and email.lower() in str(em).lower():
            ws_clean.cell(r, 4, secret_key) # Col 4 is '2fa'
    wb_clean.save(clean_v2_path)

    return True, secret_key
```

### Kết quả sau khi bật:
- Khi đăng nhập lần sau ở bất kỳ trình duyệt/máy tính/VPS nào, chỉ cần `email + password + pyotp.TOTP(secret_key).now()`.
- **Google không bao giờ hỏi hay đẩy prompt về Samsung Galaxy S7 nữa**, hoàn toàn độc lập ngay cả khi điện thoại S7 bị hỏng hay mất nguồn.

---

## 4. Quyết định Nên Dùng Phương Án Nào

| Tình huống | Phương án |
|-----------|-----------|
| S7 online nhưng cron TikTok đang chạy | **Security Code từ S7** (Section 2) $\rightarrow$ sau đó **Bật 2FA Authenticator** (Section 3) |
| S7 online và không có cron nào | Google Prompt ADB $\rightarrow$ sau đó **Bật 2FA Authenticator** |
| S7 offline / mất nguồn | Recovery Email $\rightarrow$ sau đó **Bật 2FA Authenticator** |
| Đã bật 2FA Authenticator | Đăng nhập trực tiếp bằng `pyotp.TOTP(secret).now()`, bỏ qua hoàn toàn S7 |
