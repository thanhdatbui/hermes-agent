# ChatGPT-Web Pool Watchdog Masked-Key Trap & Sentinel Recovery

## 1. Bẫy Masked Key Trên `/api/providers` (Nguyên Nhân Báo Oan `EMPTY_SESSION_TOKEN`)
- **Hiện tượng:** Watchdog kiểm tra danh sách kết nối qua `GET /api/providers`, lấy trường `apiKey` (ví dụ: `__Secure****sTow`) rồi gửi sang `POST /api/providers/validate` để kiểm tra độ sống của session token.
- **Bản chất lỗi:** Vì lý do bảo mật, OmniRoute chủ động che mờ (mask) chuỗi token khi trả về qua API. Chuỗi masked `__Secure****` là chuỗi không hợp lệ; khi gửi sang OpenAI validate sẽ luôn bị trả về HTTP 400 Bad Request.
- **Hậu quả:** Watchdog tưởng lầm rằng token đã chết, lập tức mở trình duyệt GPM lên và xóa sạch cookie (`context.clear_cookies()`) để login lại từ đầu. Nếu tài khoản không thể tự đăng nhập lại (ví dụ tài khoản Hotmail không có trong credentials hoặc Google SSO chưa đăng nhập), watchdog sẽ báo lỗi `EMPTY_SESSION_TOKEN` oan uổng cho hàng loạt tài khoản còn sống 100%.
- **Khắc phục chuẩn hóa:** KHÔNG BAO GIỜ validate bằng masked key lấy từ `/api/providers`. Bắt buộc kiểm tra liveness bằng endpoint nội bộ của OmniRoute:
  `POST http://127.0.0.1:20129/api/providers/{cid}/test` (body `{}`).
  Endpoint này tự giải mã token thật trong database `storage.sqlite` để kiểm tra trực tiếp với upstream OpenAI.

## 2. Phục Hồi Tài Khoản Dính Thử Thách Sentinel / Turnstile 403
- **Hiện tượng:** Trong quá trình vận hành, một số tài khoản bị OpenAI trả về thử thách `[403]: ChatGPT blocked the request (Sentinel/Turnstile required)`. OmniRoute tự động đánh dấu `is_active=0` và `test_status='banned'`.
- **Cơ chế hồi sinh:** Thử thách Sentinel/Turnstile mang tính tạm thời theo IP/thời điểm; bản thân session token lưu trong DB không hề bị chết hay bị thu hồi (revoked).
- **Quy trình phục hồi O(1):**
  1. Gọi `POST /api/providers/{cid}/test` kiểm tra lại.
  2. Nếu `res.valid == True`: Cập nhật trực tiếp vào SQLite:
     ```sql
     UPDATE provider_connections 
     SET is_active=1, test_status='active', last_error=NULL, last_error_at=NULL, 
         backoff_level=0, rate_limited_until=NULL, updated_at=CURRENT_TIMESTAMP 
     WHERE id=?;
     ```
  3. Tài khoản lập tức quay trở lại pool Round-Robin phục vụ mà không cần mở profile GPM.

## 3. Xử Lý Tài Khoản Gmail Hết Hạn Thật (Google SSO Checkpoint)
- **Hiện tượng:** Các tài khoản báo lỗi `ChatGPT session expired — log into chatgpt.com and copy a fresh cookie`.
- **Nguyên nhân tại GPM:** Trình duyệt GPM bị đăng xuất khỏi Google Account (`https://myaccount.google.com` chuyển hướng về landing page công khai). Khi bấm Google SSO trên ChatGPT, Google yêu cầu điền email, mật khẩu và 2FA TOTP.
- **Điều phối chuẩn:** Để `gpm-gmail-login-shifts-watchdog` tự động hoàn tất đăng nhập Google vào profile GPM trong các khung giờ nghỉ của Farm (09:30-11:20 và 15:30-17:20), sau đó watchdog mới trích xuất cookie session ChatGPT tươi nạp vào OmniRoute.
