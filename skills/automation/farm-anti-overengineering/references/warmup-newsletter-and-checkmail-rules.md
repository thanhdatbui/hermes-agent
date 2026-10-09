# Warmup Newsletter Inbound Verification & Checkmail Live Rules

## 1. Bài học xương máu: Warmup HTTP POST ảo (False Positive)
- `warmup_newsletter_services.py` dùng `urllib.request.urlopen` gửi `POST https://nodeweekly.com/subscribe` trả về `200 OK`, nhưng thực tế:
  - Form đã chuyển sang GET `https://subscribe.cooperpress.email/start?pub=node...`.
  - Phía server Cooper Press bật Cloudflare Bot Protection ("Just a moment...").
  - Response 200 thực chất là HTML trang Cloudflare Challenge, KHÔNG phải submit thành công.
  - Hậu quả: Log báo "Đã kích hoạt 4 dịch vụ newsletter" nhưng hộp thư Gmail trên thiết bị hoàn toàn trống trơn (0 email về).
- **Quy tắc**: TUYỆT ĐỐI KHÔNG tự nhận là xong nếu chưa xác thực thư thực tế trong hộp thư. Mọi luồng warmup bên thứ ba bắt buộc phải có bước kiểm chứng trên app Gmail hoặc IMAP xem thư có về thật không.

## 2. Quy trình Checkmail.live
- `checkmail.live` KHÔNG cho phép check anonymous: nếu không có `api-key`, trang sẽ alert "You are not logged in" và nút Check không chạy.
- Canonical script chuẩn: `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`.
  - Dùng Chromium Core 142 + Proxy Mobi 4G (`test.taadaa.click:5101`, user `mobi1`).
  - Hàm `ensure_logged_in_page(context)` tự động kiểm tra `document.getElementById('api-key')`. Nếu thiếu, tự động sang `login.php` giải Turnstile và tạo session.
  - Dùng `check_emails_live_batch(page, email_list, timeout_seconds=45)` nạp danh sách email vào CodeMirror `window.editor` và đọc kết quả từ `window.liveResultEditor` / `window.dieResultEditor`.
  - CẤM tự chế script Playwright checkmail mới mà không có luồng login/session check.
