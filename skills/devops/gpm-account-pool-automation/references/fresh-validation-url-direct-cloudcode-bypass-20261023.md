# Kỹ Thuật Trích Xuất Fresh `validation_url` Trực Tiếp Qua Cloud Code API (Bypass OmniRoute Model Cooldown)

## 1. Bản Chất Sự Cố & Vấn Đề Token Hết Hạn (Short-TTL Token Expired)
- Khi tài khoản Google vừa nâng Pro dính lỗi 403 `VALIDATION_REQUIRED`:
  - URL xác minh chứa tham số `plt=...` (`https://accounts.google.com/v3/signin/continue?plt=...`).
  - **Thời gian sống cực ngắn (TTL ~1-2 phút):** Nếu người dùng quét trễ hơn 1-2 phút hoặc mở lại link cũ, Google lập tức hủy token và báo:
    *"Bạn chưa đăng nhập. Phiên của bạn đã kết thúc vì không có hoạt động. Hãy thử đăng nhập lại."*
- **Bẫy OmniRoute Model Cooldown (429 ảo khi cố lấy link mới):**
  - Sau lần đầu tiên nhận 403 từ Google, OmniRoute tự động đưa connection/model vào danh sách cooldown trong bộ nhớ RAM (`model_cooldown`, reset sau 300s-600s).
  - Khi cố gắng bắn lại request qua OmniRoute (`isolated_chat_test` hoặc API proxy), OmniRoute ngắn mạch trả về `429: All credentials for model ... are cooling down` mà không hề gửi request lên Google.
  - Hậu quả: Không thể lấy được `validation_url` mới qua OmniRoute!

---

## 2. Kỹ Thuật Bắn Trực Tiếp Lên Google Cloud Code Qua Proxy Mobile
Để ép Google Cloud Code sinh ngay một `validation_url` mới tinh (fresh `plt=`), Coordinator bắn một raw HTTP request trực tiếp lên Google Cloud Code sử dụng `access_token` của tài khoản và đúng proxy của profile:

```python
import json, urllib.request, urllib.error

# 1. Đọc access_token từ sandbox AGY CLI hoặc OmniRoute DB
with open('D:/Taadaa/agy_profiles/acc_XX/.gemini/oauth_creds.json', 'r') as f:
    creds = json.load(f)
token = creds.get('access_token')

# 2. Chuẩn bị payload chuẩn cho Antigravity Cloud Code streamGenerateContent
url = 'https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}
payload = json.dumps({
    'project': 'aicode-consumers',
    'model': 'claude-sonnet-4-6',
    'request': {
        'contents': [{'role': 'user', 'parts': [{'text': 'ping'}]}]
    }
}).encode('utf-8')

# 3. Ép buộc đi qua đúng Proxy Mobile của tài khoản (tránh lộ IP direct)
proxy_handler = urllib.request.ProxyHandler({
    'http': 'http://user:pass@proxy_host:proxy_port',
    'https': 'http://user:pass@proxy_host:proxy_port'
})
opener = urllib.request.build_opener(proxy_handler)

# 4. Bắn request để hứng lỗi 403 tươi
req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
try:
    with opener.open(req, timeout=15) as resp:
        pass
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    data = json.loads(body)
    for detail in data.get('error', {}).get('details', []):
        meta = detail.get('metadata', {})
        if 'validation_url' in meta:
            fresh_validation_url = meta['validation_url']
            print('[+] FRESH_VALIDATION_URL:', fresh_validation_url)
```

---

## 3. Điều Hướng GPM & Kỷ Luật Crop Mã QR (Gate 6)
1. **Mở ngay trên GPM Profile đang chạy:**
   - Dùng Playwright CDP kết nối vào GPM profile (cổng debug hiện hành).
   - Set viewport `1280x900`.
   - `page.goto(fresh_validation_url, wait_until='domcontentloaded', timeout=30000)`.
   - Chờ 3-5s cho Google load trang *"Xác minh thông tin để tiếp tục"*.
2. **Crop cận cảnh ma trận QR (Chống quét trượt):**
   - Không chỉ chụp full màn hình (`1280x900`), Coordinator chủ động crop riêng vùng QR ma trận (tọa độ tương đối `crop = im.crop((680, 240, 1020, 530))` trên viewport `1280x900`) thành ảnh riêng `hakha_qr_pure.png`.
   - Gửi cả 2 ảnh qua `MEDIA:`: Full page để chứng minh đúng context/email, và ảnh Crop cận cảnh để camera điện thoại nhận diện mã QR lập tức dưới 0.5s.
3. **CẤM ĐÓNG TRÌNH DUYỆT (Live Handshake Invariant):**
   - Khi disconnect Playwright, TUYỆT ĐỐI CẤM gọi `browser.close()` vì sẽ đóng cả cửa sổ Chrome GPM.
   - Chỉ đóng context/page hoặc ngắt kết nối Playwright để giữ nguyên Chrome mở trực chiến trên desktop.
