# Recipe: Mua thử nghiệm tài khoản qua API Supplier (CloneFBIG / API_31) & Kiểm tra Live Facebook

## 1. Mua tài khoản test trực tiếp từ số dư Supplier trên VPS
Khi cần mua nhanh 1 tài khoản test từ nguồn kết nối (CloneFBIG, supplier `id=1`, type `API_31`) mà không cần nạp tiền qua luồng checkout frontend:

### Cú pháp gọi hàm `buy_API_31` trên VPS:
Tạo script PHP tạm thời trên VPS (ví dụ `/tmp/buy_fb_test.php`):
```php
<?php
define("IN_SITE", true);
require_once('/var/www/shopclone7/current/libs/db.php');
require_once('/var/www/shopclone7/current/config.php');
require_once('/var/www/shopclone7/current/libs/lang.php');
require_once('/var/www/shopclone7/current/libs/helper.php');
require_once('/var/www/shopclone7/current/libs/suppliers.php');

$CMSNT = new DB();
$s = $CMSNT->get_row_safe("SELECT * FROM suppliers WHERE id = 1");
if (!$s) {
    echo json_encode(["status" => "error", "msg" => "Supplier not found"]);
    exit;
}

$id_api = 15; // API ID của sản phẩm bên nguồn (ví dụ: FB Global ON 2FA)
$amount = 1;
$res = buy_API_31($s['domain'], $s['coupon'], $s['api_key'], $id_api, $amount, $s['proxy']);
echo $res;
```
Chạy: `php7.4 /tmp/buy_fb_test.php` rồi xóa file script sau khi hoàn thành.

### Định dạng trả về của CloneFBIG (`data`):
```json
{
  "status": "success",
  "msg": "Tạo đơn hàng thành công!",
  "trans_id": "5TVJ...",
  "data": [
    "UID|Password|2FA_SECRET|Cookie|Token|Email|UserAgent"
  ]
}
```

## 2. Check live nhanh Facebook UID không cần Access Token
Không cần đăng nhập hay dùng token Graph API đầy đủ, kiểm tra nhanh ảnh đại diện công khai qua Graph API:
```bash
curl -sI -m 10 "https://graph.facebook.com/<UID>/picture?type=normal" | head -n 10
```
- **HTTP/1.1 302 Found** (chuyển hướng sang CDN `fbcdn.net` ảnh đại diện): Tài khoản **LIVE**.
- **HTTP/1.1 404** hoặc không redirect: Tài khoản checkpoint, bị khóa hoặc UID không tồn tại.

## 3. Tạo mã OTP 2FA (TOTP) offline bằng Python
Khi nhận được `2FA_SECRET` (base32), có thể tạo mã OTP 6 số tức thì mà không cần truy cập website bên thứ ba (chống lộ secret):
```python
import hmac, base64, struct, hashlib, time
secret = '<2FA_SECRET>'.replace(' ', '').upper()
key = base64.b32decode(secret, True)
intervals_no = int(time.time()) // 30
msg = struct.pack('>Q', intervals_no)
h = hmac.new(key, msg, hashlib.sha1).digest()
o = h[19] & 15
otp = (struct.unpack('>I', h[o:o+4])[0] & 0x7fffffff) % 1000000
print(f"OTP: {otp:06d}")
```
