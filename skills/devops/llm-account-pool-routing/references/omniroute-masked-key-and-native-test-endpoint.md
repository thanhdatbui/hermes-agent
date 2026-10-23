# OmniRoute Masked Key Trap & Native Provider Test Endpoint

## Context & Symptom (2026-10-24 Incident)
Trong báo cáo sức khỏe watchdog định kỳ (`chatgpt-web-pool-healer-watchdog`), hệ thống báo cáo hàng loạt tài khoản ChatGPT-Web (26 tài khoản) gặp lỗi:
```text
Validate fail: EMPTY_SESSION_TOKEN
```
hoặc
```text
Validate fail: HTTP Error 400: Bad Request
```
Dẫn tới watchdog kết luận sai rằng token đã chết, tự động kích hoạt Playwright CDP mở GPM profile lên, xóa sạch cookie (`context.clear_cookies()`) và cố gắng đăng nhập lại từ đầu, gây lãng phí tài nguyên và làm kẹt profile.

## Root Cause: Masked API Key in `/api/providers`
1. **API Key Masking:** Khi watchdog gọi endpoint `GET http://127.0.0.1:20129/api/providers`, OmniRoute bảo mật thông tin bằng cách che chuỗi token/key thành dạng mask (ví dụ: `__Secure****sTow` hoặc `eyJhbG****1234`).
2. **Validate Mù:** Script watchdog cũ lấy trực tiếp chuỗi masked này gửi sang endpoint `POST /api/providers/validate` với payload `{"provider": "chatgpt-web", "apiKey": cur_key}`.
3. OpenAI và OmniRoute từ chối chuỗi key bị che giấu với lỗi `400 Bad Request` hoặc coi là rỗng (`EMPTY_SESSION_TOKEN`).
4. **Hậu quả:** 15/23 tài khoản thực tế có session token hoàn toàn sống 100% trong database SQLite (`storage.sqlite`), nhưng bị watchdog phán tử hình và cố gắng đăng nhập lại trong vô vọng.

## Correct Engineering Pattern: Native Test Endpoint
Khi muốn kiểm tra liveness của một connection đã tồn tại trên OmniRoute (:20129), **TUYỆT ĐỐI KHÔNG** lấy chuỗi key che giấu từ `/api/providers` để validate.

BẮT BUỘC gọi trực tiếp endpoint kiểm thử nội bộ:
```http
POST http://127.0.0.1:20129/api/providers/{cid}/test
Content-Type: application/json

{}
```

### Ưu điểm vượt trội:
- **Zero-Token Decryption:** OmniRoute tự trích xuất và giải mã (decrypt) chuỗi `api_key` thật được lưu trữ trong bảng `provider_connections` của SQLite.
- **Upstream Validation:** OmniRoute gửi request kiểm tra trực tiếp tới upstream API và trả về kết quả chuẩn:
  ```json
  {
    "valid": true,
    "error": null,
    "warning": null,
    "latencyMs": 591,
    "testedAt": "2026-10-23T17:34:56.125Z"
  }
  ```
- **Sentinel Recovery:** Nếu tài khoản trước đó bị tạm khóa do thử thách Sentinel / Turnstile (`ChatGPT blocked the request`), khi thử thách hết hiệu lực, gọi endpoint này sẽ xác nhận ngay `valid: true`. Watchdog chỉ cần cập nhật lại `is_active=1`, `test_status='active'`, xóa `last_error` trong database là tài khoản phục hồi ngay lập tức trong 500ms mà không cần chạm vào trình duyệt.
