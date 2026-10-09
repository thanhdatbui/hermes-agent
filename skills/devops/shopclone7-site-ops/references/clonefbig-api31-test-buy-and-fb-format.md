# CloneFBIG API_31 Test Buy, Account Formats, & Live Verification

## 1. Direct Purchase via Connector (`buy_API_31`)

To test-purchase an account directly from CloneFBIG (API_31) via PHP CLI on the VPS (without frontend order creation):

```php
define("IN_SITE", true);
require_once('/var/www/shopclone7/current/libs/db.php');
require_once('/var/www/shopclone7/current/config.php');
require_once('/var/www/shopclone7/current/libs/lang.php');
require_once('/var/www/shopclone7/current/libs/helper.php');
require_once('/var/www/shopclone7/current/libs/suppliers.php');

$CMSNT = new DB();
$s = $CMSNT->get_row_safe("SELECT * FROM suppliers WHERE id = 1");
if (!$s) { die("Supplier 1 not found"); }

// $id_api is the source product ID (e.g. 15 for Facebook Name Global 15-30 days 2FA)
$res = buy_API_31($s['domain'], $s['coupon'], $s['api_key'], $id_api, $amount, $s['proxy']);
echo $res;
```

**Response Format:**
```json
{
  "status": "success",
  "msg": "Tạo đơn hàng thành công!",
  "trans_id": "5TVJ6ac50b9faeebc",
  "data": [
    "UID|Password|2FA|Cookie|Token|Email|UserAgent"
  ]
}
```

## 2. Facebook Clone Account Fields Breakdown
When purchased with 2FA enabled, the data string uses pipe (`|`) delimiters:
- `data[0]`: UID (e.g. `61594276057261`)
- `data[1]`: Password
- `data[2]`: 2FA Base32 Secret Key (e.g. `5DAAMOLIASIPNSH7`)
- `data[3]`: Full Cookie string (`c_user=...;xs=...;fr=...;`)
- `data[4]`: Access Token (`EAAAAU...`)
- `data[5]`: Registered Email (e.g. TempMail / `@fextemp.com`)
- `data[6]`: Mobile User-Agent string

## 3. Fast Live Check for FB Clone UIDs
Check whether the UID is still live on Facebook without logging in or risking bot detection:
```bash
curl -sI -m 10 "https://graph.facebook.com/<UID>/picture?type=normal" | head -n 10
```
- `HTTP/1.1 302 Found` with redirect to `fbcdn.net` avatar = **LIVE**.
- Error / Graph API exception = **CHECKPOINT / BANNED / NOT FOUND**.

## 4. Pure Python TOTP Generation (No External Libs)
Generate a 6-digit 2FA OTP from the Base32 secret without requiring `pyotp`:
```python
import hmac, base64, struct, hashlib, time

secret = "5DAAMOLIASIPNSH7"
key = base64.b32decode(secret, True)
intervals_no = int(time.time()) // 30
msg = struct.pack(">Q", intervals_no)
h = hmac.new(key, msg, hashlib.sha1).digest()
o = h[19] & 15
otp = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
print(f"OTP: {otp:06d}")
```

## 5. Bẫy Acc Clone 'Android Registration' khi dùng cho Web OAuth (Meta Anti-Fraud)
- **Bản chất tài khoản clone giá rẻ:** 100% tài khoản clone bán trên shop (CloneFBIG / Doravo) được tạo và nuôi tự động trên Facebook/Instagram Mobile App Android (`UA APP`).
- **Hành vi bất thường môi trường (Environment Jump):** Khi đăng nhập trực tiếp trên Desktop Web Browser (Chrome PC, GPM) qua IP proxy mới:
  - Meta phát hiện nhảy vọt môi trường từ Android sang Windows Desktop.
  - Meta sẽ KHÔNG hỏi OTP 2FA ngay mà lập tức kích hoạt:
    1. **WhatsApp OTP:** Gửi mã về WhatsApp cài trên SĐT gốc của người tạo (đầu số `+216...`).
    2. **Google reCAPTCHA Enterprise (`referer_frame.php`):** Bắt giải captcha hình ảnh người thật.
- **Giải pháp:** Nếu mục tiêu là xác minh tuổi (Age Verification), ưu tiên nhập thẻ thanh toán Visa/Mastercard ($0 authorization). Nếu bắt buộc dùng Facebook/Instagram, phải đăng nhập trên thiết bị Android thật trước để xác nhận thiết bị tin cậy.

