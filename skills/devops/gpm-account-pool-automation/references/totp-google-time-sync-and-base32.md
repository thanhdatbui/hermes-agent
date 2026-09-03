# Google 2FA TOTP: Clock Synchronization and Base32 Key Formatting

## 1. Vấn đề lệch Clock Skew hệ thống Windows gây "Sai mã 2FA"

### Hiện tượng:
- Khi điền mã 2FA từ `pyotp.TOTP(secret).now()`, Google liên tục trả về: `Sai mã. Hãy thử lại.` mặc dù secret key hoàn toàn chính xác.

### Nguyên nhân:
- Thuật toán TOTP (Time-based One-Time Password - RFC 6238) chia thời gian thành các time-step 30 giây dựa trên Unix Timestamp UTC (`time.time()`).
- Trên một số máy Windows hoặc môi trường dev có timezone UTC+7 nhưng system clock / daylight savings không đồng bộ chuẩn UTC, `time.time()` bị lệch (ví dụ lệch 25200 giây = đúng 7 tiếng), khiến mã OTP sinh ra bị tính trước 7 tiếng so với Google Server.

### Giải pháp chuẩn (Lấy True UTC Timestamp từ Google HTTP Date):
```python
import time
import urllib.request
import email.utils
import pyotp

def get_google_server_utc_time() -> float:
    """Lấy Unix timestamp UTC chuẩn trực tiếp từ Google HTTP Date header."""
    try:
        req = urllib.request.urlopen("https://www.google.com", timeout=3)
        date_header = req.headers.get("Date")
        if date_header:
            return time.mktime(email.utils.parsedate(date_header))
    except Exception:
        pass
    # Fallback: nếu hệ thống lệch +7h (25200s)
    return time.time() - 25200

def generate_google_totp(secret_key: str) -> str:
    """Sinh mã 2FA Google Authenticator chuẩn xác tuyệt đối theo giờ Google."""
    # Chuẩn hóa Base32 key: bỏ khoảng trắng và chuyển chữ hoa
    clean_secret = secret_key.strip().replace(" ", "").upper()
    totp = pyotp.TOTP(clean_secret)
    google_utc = get_google_server_utc_time()
    return totp.at(google_utc)
```

---

## 2. Định dạng Secret Key 2FA Base32 vs Non-Base32

### Khóa chuẩn (RFC 3548 Base32):
- Chỉ bao gồm các ký tự: chữ cái `A-Z` (không phân biệt hoa thường) và số `2-7`.
- Độ dài: 16 hoặc 32 ký tự (thường nhóm 4 hoặc 8 ký tự, ví dụ: `obnr 2a2q w3ch sbyk zmja jidp ywfu yrai` hoặc `RCFJLTXPCDW3TCV3US4FB5CUBOPXHSUX`).

### Dấu hiệu khóa sai / thô:
- Chứa các chữ số `8`, `9` hoặc ký tự đặc biệt.
- Khóa này không phải là secret TOTP trực tiếp mà có thể là chuỗi hash/token nội bộ cần giải mã trước.

---

## 3. Quy trình Login 2FA tự động qua Playwright CDP

```python
# Kiểm tra input TOTP trên trang Google
totp_input = page.locator('input[type="tel"], input#totpPin, input[name="totpPin"]')
if totp_input.count() > 0:
    otp_code = generate_google_totp(totp_secret)
    totp_input.first.fill(otp_code)
    page.locator('#totpNext, button:has-text("Tiếp theo"), button:has-text("Next")').first.click()
    page.wait_for_timeout(4000)
```
