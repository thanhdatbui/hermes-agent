# Google Sign-in v3 Post-Password Challenges, Passkey Speedbump & URL Parsing Pitfalls (2026-09-05)

## 1. Passkey Speedbump vs TOTP Selector Collision
### Triệu chứng
- Sau khi nhập password thành công, Google chuyển sang trang:
  `https://accounts.google.com/v3/signin/speedbump/passkeyenrollment` (Tiêu đề: *"Đơn giản hóa việc đăng nhập bằng mã khóa"*).
- Script tự động hoá bị treo 35s (`playwright._impl._errors.TimeoutError: Locator.click: Timeout 35000ms exceeded waiting for #totpNext`).
- Nguyên nhân: Selector TOTP dùng broad matching `input[type="tel"]` bị dính phần tử tel ẩn/phụ trợ trên trang passkey enrollment, khiến script hiểu lầm đây là màn hình nhập 2FA và cố bấm nút `#totpNext` vốn không tồn tại trên trang passkey.

### Cách khắc phục chuẩn
1. **Ưu tiên Dismiss Passkey/Onboarding trước TOTP:**
   Luôn quét và click các nút bỏ qua trước khi xử lý TOTP:
   ```python
   dismiss_selectors = [
       'button:has-text("Không phải bây giờ")',
       'button:has-text("Not now")',
       'button:has-text("Bỏ qua")',
       'button:has-text("Để sau")',
       'button:has-text("Skip")',
       'button:has-text("Hủy")',
       'button:has-text("Lúc khác")'
   ]
   for d_sel in dismiss_selectors:
       btn = page.locator(d_sel)
       if btn.count() > 0 and btn.first.is_visible():
           btn.first.click()
           time.sleep(3)
           break
   ```
2. **Thu hẹp Selector TOTP:**
   Chỉ kích hoạt điền TOTP khi:
   - Ô nhập thực sự mang id/name TOTP: `input#totpPin, input[name="totpPin"], input#idvPinId, input[name="Pin"]`
   - Hoặc URL hiện tại chứa chuỗi `"totp"` (ví dụ `challenge/totp`) kết hợp `input[type="tel"]`.
   - Khi click nút next của TOTP, luôn giới hạn timeout ngắn: `page.locator('#totpNext, button:has-text("Tiếp theo")').first.click(timeout=5000)`.

---

## 2. Lỗi Kiểm tra URL Callback (Query Parameter Match Pitfall)
### Triệu chứng
- Khi Google đăng nhập thành công hoặc chuyển tiếp sang các trang xác minh sau login:
  - `https://myaccount.google.com/verification/selfie/precollection?next=https://accounts.google.com/ServiceLogin?...`
  - `https://gds.google.com/web/recoveryoptions?continue=https%3A%2F%2Faccounts.google.com%2FServiceLogin?...`
- Điều kiện kiểm tra session thường dùng:
  ```python
  if "myaccount.google.com" in current_url and "signin" not in current_url and "servicelogin" not in current_url:
  ```
- Kết quả: Biểu thức luôn trả về `False` vì `ServiceLogin` hoặc `signin` nằm trong chuỗi tham số query (`next=...` hoặc `continue=...`), khiến script bị kẹt duyệt 10-12 bước vô nghĩa dù user đã authenticated 100%!

### Cách khắc phục chuẩn
Dùng `urllib.parse.urlparse` để chỉ so khớp domain (`netloc`) và đường dẫn thực (`path`), loại bỏ hoàn toàn phần query parameters:
```python
import urllib.parse

parsed = urllib.parse.urlparse(current_url.lower())
is_authenticated = (
    ("myaccount.google.com" in parsed.netloc and "signin" not in parsed.path and "servicelogin" not in parsed.path)
    or "recoveryoptions" in parsed.path 
    or "precollection" in parsed.path
)
if is_authenticated:
    # Tài khoản đã login thành công, điều hướng trực tiếp về https://myaccount.google.com/ để xác nhận DOM
```

---

## 3. Lỗi `TargetClosedError` khi gọi `page.title()` / `page.url` giữa chừng redirect
### Triệu chứng
- Ngay sau khi submit password hoặc recovery email, Google thực hiện navigation / refresh trang hoặc đóng tab trung gian.
- Nếu gọi `page.title()` hoặc `page.locator("body").inner_text()` ngay lập tức mà không bọc `try/except`, Playwright sẽ ném ngoại lệ:
  `playwright._impl._errors.TargetClosedError: Page.title: Target page, context or browser has been closed`.

### Cách khắc phục chuẩn
1. Luôn bọc các lệnh đọc trạng thái trang (`page.url`, `page.title()`, `inner_text()`) trong khối `try/except Exception: pass`.
2. Kiểm tra `if page.is_closed():` -> fallback sang trang còn mở trong context:
   ```python
   active_page = page
   if active_page.is_closed():
       reg_pages = [p for p in context.pages if not p.url.startswith("chrome-extension://") and not p.is_closed()]
       if reg_pages:
           active_page = reg_pages[0]
   ```
