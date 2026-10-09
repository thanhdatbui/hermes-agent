# Chính sách cấu hình Mail cho TikTok Reg & On-demand Provisioning (2026-09)

## 1. Tạm thời tắt đăng ký TikTok qua Gmail
- **Lý do**: Tài khoản Gmail cũ thường xuyên gặp lỗi timeout OTP (`[7c][BLOCKED_GMAIL_OTP_TIMEOUT]`) do bảo mật Google chặn IMAP/POP3, checkpoint hoặc trễ nhận mã từ TikTok.
- **Quy định**: Toàn bộ luồng đăng ký TikTok (`Tiktok_Reg`) và cấp tài khoản tự động (`ensure_row_accounts.py`) tạm thời chỉ sử dụng các domain Microsoft OAuth2 (`@hotmail.com`, `@outlook.com`, `@live.com`).

## 2. Vị trí cấu hình chuẩn
- `D:\Taadaa\Tiktok_Reg\scripts\tiktok_target_eligibility.py`:
  ```python
  # Tạm thời tắt @gmail.com khi reg TikTok do hay bị timeout OTP/checkpoint
  SUPPORTED_DOMAINS = ("@hotmail.com", "@outlook.com", "@live.com")
  ```
- `D:\Taadaa\tools\ensure_row_accounts.py`:
  Hàm `get_available_mails_by_machine` bắt buộc lọc bỏ các mail đuôi `@gmail.com` để nếu máy chỉ có sẵn Gmail trong kho thì script vẫn kích hoạt mua Hotmail OAuth2 bổ sung qua `buy_hotmail.py`.

## 3. Kênh nhận báo cáo Preflight Reg bù
- Telegram chat ID mặc định cho `ensure_row_accounts.py` là **Farm Alert** (`-5373649734`), tuyệt đối không gửi về nhóm Gmail reg (`-5139245637`).
