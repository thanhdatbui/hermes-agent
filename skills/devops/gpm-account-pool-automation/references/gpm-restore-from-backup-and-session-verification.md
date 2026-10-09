# GPM Profile Restore from Zip Backup & Session Verification Guide

## Quy trình Khôi phục Profile từ Zip Backup và Xác minh Session Google

### 1. Chuẩn bị & Dọn dẹp Tiến trình (Bắt buộc)
Trước khi giải nén hoặc ghi đè file profile, phải kill toàn bộ tiến trình `chrome.exe` và `gpmdriver.exe` để giải phóng lock trên `Default\Network\Cookies` và SQLite DB:

```python
import psutil

for p in psutil.process_iter(['pid', 'name']):
    try:
        name = p.info['name'].lower()
        if any(x in name for x in ['chrome', 'gpmdriver', 'chromedriver']):
            p.kill()
    except Exception:
        pass
```

### 2. Giải nén Thư mục Profile từ Zip Backup
Giải nén chính xác thư mục profile tương ứng từ `D:\OneDrive\backup\GPM\gpm_active_16profiles_YYYYMMDD.zip` hoặc `gpm_hidden_240profiles_YYYYMMDD.zip` vào `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\`:

```python
import zipfile, os

zip_path = r'D:\OneDrive\backup\GPM\gpm_active_16profiles_20260901.zip'
dest_dir = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile'
targets = ['3_s5w5k', '4_hmmy5', '5_vqxmk']

with zipfile.ZipFile(zip_path, 'r') as z:
    all_files = z.namelist()
    target_files = [f for f in all_files if any(f.startswith(t + '/') or f == t for t in targets)]
    for member in target_files:
        z.extract(member, path=dest_dir)
```

### 3. Đồng bộ Database & Bảo tồn Tuyệt đối Fingerprint Gốc
- **Backup DB trước khi UPDATE:** Sao lưu `profile_data.db` sang `profile\_backup\profile_data_pre_restore_YYYYMMDD_HHMMSS.db`.
- **Lấy `JsonData` gốc:** Đọc trực tiếp từ `profile_data_backup.db`.
- **Chỉ cập nhật trường Proxy:** Gán proxy chuẩn của S7 Farm (`test.taadaa.click:5101..5138` / Singbox `20001..20074`), giữ nguyên 100% các trường:
  - `AudioNoise`
  - `CanvasNoiseToken`
  - `WebGLRenderer`
  - `WebGLVendor`
  - `MacAddress`
  - `UserAgent`

### 4. Khởi động GPM API & Kết nối Playwright CDP
1. Start profile qua GPM Local API:
   ```python
   import requests
   res = requests.get(f'http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}').json()
   cdp_addr = res['data']['remote_debugging_address']
   ```
2. Kết nối Playwright:
   ```python
   from playwright.sync_api import sync_playwright

   with sync_playwright() as p:
       browser = p.chromium.connect_over_cdp(f'http://{cdp_addr}')
       context = browser.contexts[0]
       page = context.pages[0] if context.pages else context.new_page()
       
       # Check MyAccount
       page.goto('https://myaccount.google.com/', wait_until='domcontentloaded', timeout=30000)
       
       # Check Gmail Inbox
       page.goto('https://mail.google.com/mail/u/0/#inbox', wait_until='domcontentloaded', timeout=30000)
   ```

### 5. Nhận diện Trạng thái Session Google
- **Session LIVE (Không cần login lại):**
  - MyAccount title: `Tài khoản Google` (URL: `https://myaccount.google.com/`).
  - Gmail title: `Hộp thư đến (...) - <email> - Gmail`.
  - Nút user account hiển thị email và tên đầy đủ.
- **Session EXPIRED (Hết hạn cookie phiên / Cần mật khẩu):**
  - Chuyển hướng về `https://accounts.google.com/v3/signin/accountchooser` hoặc `accounts/SetOSID` (Error 400).
  - DOM hiển thị tên tài khoản + email kèm trạng thái `"Đã đăng xuất"` hoặc yêu cầu xác nhận mật khẩu.

### 6. Dọn dẹp Sau Khi Test
- Gọi API stop profile: `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.
- Chạy quét dọn tiến trình mồ côi `chrome.exe` / `gpmdriver.exe` để không tràn RAM và tránh kẹt port CDP.
