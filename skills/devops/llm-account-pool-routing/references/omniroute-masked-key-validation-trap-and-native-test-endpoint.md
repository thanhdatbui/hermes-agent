# OmniRoute Masked Key Validation Trap & Native Test Endpoint

## Hiện tượng (Bẫy False-Negative Token Dead)
Khi kiểm tra sức khỏe các connection trên OmniRoute (`:20129`), endpoint `GET /api/providers` trả về danh sách connection nhưng trường `apiKey` đã bị bảo mật bằng cơ chế che giấu (masking):
- Ví dụ ChatGPT Web: `__Secure****sTow` thay vì toàn bộ chuỗi session token.
- Ví dụ API Key thường: `sk-****abcd`.

Nếu watchdog hoặc script chẩn đoán tự động lấy `c.get('apiKey')` rồi gửi sang endpoint `POST /api/providers/validate`:
- Endpoint `/validate` nhận chuỗi masked string `__Secure****sTow` coi đó là token thật và gửi sang upstream OpenAI.
- OpenAI từ chối (HTTP 400 Bad Request / Invalid Token).
- Script tự suy diễn sai rằng session token của tài khoản đã chết (`EMPTY_SESSION_TOKEN` hoặc `Validate fail`), kích hoạt luồng cứu hộ không cần thiết: mở profile GPM, xóa sạch cookie trong trình duyệt (`context.clear_cookies()`), gây phá vỡ các session đang sống.

## Giải pháp chuẩn hóa (Native Test Endpoint)
OmniRoute đã cung cấp sẵn endpoint kiểm tra sống/chết (liveness) chuẩn xác cho từng connection cụ thể:
```http
POST http://127.0.0.1:20129/api/providers/{cid}/test
Content-Type: application/json

{}
```

### Ưu điểm vượt trội:
1. **Zero-Leak & Không cần giải mã:** OmniRoute tự động trích xuất và giải mã `api_key` thật lưu trong `storage.sqlite` để gửi đi test upstream.
2. **Chính xác 100%:** Trả về kết quả JSON có cấu trúc:
   - `valid: true` kèm latency -> token còn sống, tài khoản hoàn toàn khỏe mạnh.
   - `valid: false` kèm `error` chi tiết (`ChatGPT session expired`, `Sentinel required`, ...).
3. **Phục hồi trong $O(1)$:** Nếu `valid: true` nhưng connection đang bị `is_active=0` do rate limit hoặc Sentinel tạm thời trước đó, chỉ cần cập nhật SQLite:
   ```sql
   UPDATE provider_connections 
   SET is_active=1, test_status='active', last_error=NULL, last_error_at=NULL, backoff_level=0, rate_limited_until=NULL, updated_at=CURRENT_TIMESTAMP 
   WHERE id=?;
   ```
   Tài khoản được hồi sinh ngay lập tức trong 1 giây mà không cần mở trình duyệt hay chạm vào GPM profile.
