# Quy tắc Xử lý Timeout OTP Gmail khi Login TikTok & Check Live Siêu Tốc qua checkmail.live (2026-09-02)

## 1. Bối cảnh & Yêu cầu từ User
Khi chạy script `reconcile_tiktok_accounts.py` / `tiktok_login_v1.py` để đăng nhập bù tài khoản TikTok trên máy nông trại:
- Khi tài khoản yêu cầu OTP gửi về Gmail nhưng gặp lỗi **`BLOCKED_GMAIL_OTP_TIMEOUT`** (do Gmail app chưa đồng bộ hoặc OTP về trễ):
- **User Rule (Bắt buộc):** 
  1. Khi fail lấy OTP, **BẮT BUỘC** phải kiểm tra xem Gmail đó có còn **LIVE** hay không.
  2. **Nếu Gmail DIE:** Báo cáo lại cho user và dọn dẹp account/workbook theo đúng quy trình.
  3. **Nếu Gmail LIVE:** Không được dừng vô cớ hoặc tự ý kết luận lỗi nick; **tiếp tục script login** (kéo refresh inbox / retry login).

---

## 2. Phương pháp Check Live Gmail Siêu Tốc qua `checkmail.live` (Chrome CDP 9222)
Không cần chạy probe `check_google_live_with_core` trên điện thoại làm tốn thời gian; dùng trực tiếp Chrome CDP port 9222 với session đã lưu sẵn của Hermes:

### Khởi động Chrome CDP (nếu chưa chạy):
```python
import subprocess, time, urllib.request

cmd = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '--remote-debugging-port=9222',
    r'--user-data-dir=C:\Users\Kibe\AppData\Local\hermes\browser_profile',
    '--no-first-run',
    '--no-default-browser-check'
]
subprocess.Popen(cmd)
time.sleep(2)
```

### Đoạn mã kiểm tra nhanh qua Playwright CDP:
```python
import time, re
from playwright.sync_api import sync_playwright

def check_gmail_fast_live(email: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        check_page = None
        for pg in context.pages:
            if 'checkmail.live' in pg.url:
                check_page = pg
                break
        if not check_page:
            check_page = context.new_page()
            check_page.goto('https://checkmail.live/', wait_until='domcontentloaded')
            time.sleep(2)
        
        check_page.bring_to_front()
        time.sleep(0.5)
        
        # Set email vào CodeMirror editor và trigger check
        check_page.evaluate(f"""() => {{
            if (window.editor) window.editor.setValue('{email}');
            if (window.liveResultEditor) window.liveResultEditor.setValue('');
            const btn = document.getElementById('btn-check');
            if (btn) btn.click();
        }}""")
        
        for _ in range(15):
            time.sleep(1)
            val = check_page.evaluate('window.liveResultEditor ? window.liveResultEditor.getValue() : ""')
            if val and email in val:
                return 'LIVE' if '[live]' in val.lower() else 'DIE'
        return 'UNKNOWN'
```

---

## 3. Quy trình Quyết định (Decision Matrix)
1. **Kết quả LIVE:** 
   - Kích hoạt lại `reconcile_tiktok_accounts.py` hoặc `login_one_account`.
   - Trên thiết bị: Thực hiện mở Gmail app, vuốt kéo từ trên xuống (Pull-to-refresh) ở tab Hộp thư đến / Quảng cáo để ép Google Play Services đồng bộ mail mới nhất về máy.
2. **Kết quả DIE:** 
   - Chụp screencap bằng chứng.
   - Báo cáo rõ ràng cho user: Mail DIE -> Xin chỉ đạo thay thế nick mới hoặc xóa slot theo đúng quy định phân biệt giữa TikTok và Gmail.
