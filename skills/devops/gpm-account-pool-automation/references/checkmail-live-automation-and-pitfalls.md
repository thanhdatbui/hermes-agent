# Checkmail.live Automation: Pitfalls, Auth Flow & Direct Verification

## 1. Bản chất dịch vụ Checkmail.live
- **Yêu cầu bắt buộc Authenticated Session**: Trang `checkmail.live` **KHÔNG** cho phép check nặc danh (guest check). Bấm nút `#btn-check` khi chưa có session sẽ lập tức gọi `alert('You are not logged in')` và dừng thực thi.
- **Cơ chế API Key**: Khi đã đăng nhập, `document.getElementById('api-key').value` sẽ mang chuỗi token session (ví dụ `b54a07fb...`). Nếu key này rỗng, request kiểm tra sẽ không bao giờ được gửi đi.
- **Tránh nhầm lẫn False Positive/Timeout**: Nếu script Playwright chỉ nhập text vào CodeMirror rồi click `#btn-check` mà không duy trì session hoặc không bypass login trước, UI vẫn đứng im ở nhãn `Check`, bộ đếm `0/0/0` không nhảy, dẫn đến timeout hoặc kết luận sai.

## 2. Canonical Script & Môi trường thực thi
Toàn bộ logic chuẩn về tự động đăng nhập, duy trì session, và check batch tài khoản được lưu tại:
`D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`

### Các thành phần cốt lõi:
1. **Chrome Executable**:
   - `C:/Users/Kibe/AppData/Local/Programs/GPMLogin/gpm_browser/gpm_browser_chromium_core_142/chrome.exe`
2. **Persistent User Data Dir**:
   - `D:/Taadaa/GPM auto/checkmail_proxy_data`
   - *Lưu ý*: Không chạy 2 process Playwright cùng đè vào một thư mục `USER_DATA_DIR` này cùng lúc vì sẽ dính lỗi lock file / `Failed to decrypt: Key not valid for use in specified state`.
3. **Proxy Egress**:
   - Bắt buộc chạy qua mobile proxy port sạch của farm (ví dụ `test.taadaa.click:5101` user `mobi1`).
4. **Luồng tự động Login / Self-healing**:
   - Hàm `ensure_logged_in_page(context)`: Kiểm tra `#api-key`. Nếu mất session, tự động điều hướng sang `https://checkmail.live/login.php`, click nút chuyển sang form đăng ký (`#switch-c2 .switch-btn`), tạo user tạm thời (ephemeral account), đợi Cloudflare Turnstile token (`cf-turnstile-response`) và submit form để lấy lại API key mới.

## 3. Cách gọi kiểm tra nhanh (Python Helper)
Thay vì tự viết lại Playwright từ đầu trong các tool script nhỏ, import trực tiếp từ canonical script:

```python
import sys
sys.path.insert(0, r"D:/Taadaa/GPM auto/scripts")
from run_checkmail_kibe_farm import (
    check_emails_live_batch,
    ensure_logged_in_page,
    FARM_PROXY_SERVER,
    FARM_PROXY_USER,
    FARM_PROXY_PASS,
    CHROME_EXEC,
    USER_DATA_DIR
)
from playwright.sync_api import sync_playwright

proxy = {"server": FARM_PROXY_SERVER, "username": FARM_PROXY_USER, "password": FARM_PROXY_PASS}

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        executable_path=CHROME_EXEC,
        headless=True,
        proxy=proxy,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = ensure_logged_in_page(context)
    results = check_emails_live_batch(page, ["email_can_check@gmail.com"], timeout_seconds=45)
    print(results)  # {'email_can_check@gmail.com': 'LIVE' hoặc 'DIE'}
    context.close()
```

## 4. Bẫy kiểm tra Live vs Checkpoint (SMS Challenge)
- Khi một Gmail bị Google kích hoạt cờ `challenge/iap` (bắt xác minh số điện thoại trên máy / web Google): `checkmail.live` sẽ phân loại tài khoản đó là **DIE** (do không thể xác thực hòm thư hoặc hòm thư đã bị phong tỏa).
- Khi phát hiện `DIE` qua `checkmail.live`:
  1. Tạo bản sao lưu (backup) trước khi sửa đổi: `gmail_clean_v2_backup_<timestamp>.xlsx`.
  2. Xóa hàng tài khoản đó khỏi `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`.
  3. Để lại slot máy trống để các batch reg đêm tự động reg bù tài khoản sạch mới.
