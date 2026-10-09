# Hotmail OAuth Token Bypass & 5SIM Dynamic Pool Rotation

## 1. Hotmail Token Bypass Architecture (Two-branch Strategy)
Khi thực hiện chu kỳ Hotmail -> ChatGPT -> Codex:
- **Tài khoản ĐÃ CÓ OAuth Token (Microsoft Graph refresh_token):**
  - **BỎ QUA 100% bước HOTMAIL_LOGIN** (không mở web `login.live.com` qua proxy GPM). Việc mở webmail bằng mật khẩu qua proxy lạ sẽ khiến Microsoft kích hoạt Security Checkpoint bắt xác minh mail khôi phục (như `@fviainboxes.com`).
  - GPM Profile mở thẳng `chatgpt.com` để chạy `CHATGPT_REG`.
  - Khi OpenAI gửi mã xác nhận 6 số về Hotmail, backend script trên PC tự động gọi Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages`) bốc OTP trực tiếp trong vòng 2 giây mà không cần tương tác UI webmail.
- **Tài khoản CHƯA CÓ OAuth Token:**
  - Bắt buộc phải chạy `HOTMAIL_LOGIN` trên GPM để vào webmail lấy OTP.
  - Đối với mail khôi phục dạng domain temp-mail công khai (ví dụ `@fviainboxes.com`): có thể truy cập trực tiếp `https://fviainboxes.com`, điền prefix email và xem hòm thư để lấy code giải phóng tài khoản.

## 2. Dynamic 5SIM Live Pool Rotation (< $0.15)
- Không dùng mảng tĩnh fix cứng quốc gia hoặc giới hạn max_attempts quá thấp (`max_attempts=2` dễ bị fail khi quốc gia đầu hết số và quốc gia thứ 2 không về SMS).
- Gọi trực tiếp `get_live_pool(max_price=0.15)` từ API `https://5sim.net/v1/guest/prices?product=openai`.
- Quy tắc sắp xếp độ ưu tiên:
  1. **Ưu tiên Việt Nam** (`virtual34`, `virtual47`) theo chỉ đạo User.
  2. **Tỷ lệ về SMS cao nhất (rate24 desc)**: Hy Lạp (`virtual66`/`virtual34`), Anh (`virtual34`), Thái Lan, Philippines...
  3. **Giá rẻ nhất (cost asc)**: quanh $0.05 - $0.12.
- Thiết lập **5 lượt thử liên hoàn (max_attempts=5)**:
  - Timeout chờ SMS tối ưu: **45s** (thay vì 90s). Nếu sau 45s không có SMS -> lập tức gọi `cancel_number` trên 5SIM để hoàn tiền 100% và chuyển tiếp quốc gia kế tiếp trong pool.
  - Phím tắt chọn quốc gia Việt Nam trên dropdown OpenAI: gõ `'Viet'` + `Enter`.
  - Luôn gửi `Escape` sau khi chọn xong quốc gia trong popover để đóng dropdown overlay, tránh lỗi `Element intercepts pointer events` khi click hoặc fill `input[type="tel"]`.
