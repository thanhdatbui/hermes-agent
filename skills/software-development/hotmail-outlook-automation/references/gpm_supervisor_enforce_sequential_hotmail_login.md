# Bắt buộc tuần tự HOTMAIL_LOGIN -> CHATGPT_REG (GPM Supervisor)

## Quy tắc cốt lõi (2026-10-13)
- **CẤM NHẢY CÓC BỎ QUA HOTMAIL_LOGIN:** Dù tài khoản đã có sẵn OAuth refresh token (cột 9 trong `gmail_clean_v2.xlsx`), profile GPM **BẮT BUỘC** phải được mở lên để đăng nhập vào Microsoft `login.live.com` và lưu cookie/session hoàn chỉnh.
- **Vai trò của OAuth Token:** Token Microsoft Graph API chỉ dùng để bóc mã OTP qua API khi có dịch vụ gửi mail xác minh (như đăng ký ChatGPT), **TUYỆT ĐỐI KHÔNG ĐƯỢC DÙNG ĐỂ BỎ QUA BƯỚC ĐĂNG NHẬP TRÌNH DUYỆT GPM**.
- **Chu trình State Machine chuẩn:**
  $$\mathbf{HOTMAIL\_LOGIN} \longrightarrow \mathbf{CHATGPT\_REG} \longrightarrow \mathbf{WAIT\_7D} \longrightarrow \mathbf{CHANGE\_INFO} \longrightarrow \mathbf{DONE}$$

## Pitfall đã khắc phục
- **Bug cũ trong `batch_gpm_5profiles_supervisor.py`:**
  - Logic cũ tự ý gán `initial_stage = "CHATGPT_REG" if has_token else "HOTMAIL_LOGIN"` và tự nâng stage `HOTMAIL_LOGIN -> CHATGPT_REG` khi thấy email có token.
  - Hậu quả: Toàn bộ 619 nick Farm Admin (đều có sẵn token) bị gạt phăng khỏi bước đăng nhập Hotmail, khiến hàng trăm profile GPM chưa từng được đăng nhập tài khoản Hotmail lên trình duyệt.
  - Khắc phục: Khóa cứng `fresh_info` luôn khởi tạo stage là `HOTMAIL_LOGIN` và xóa bỏ toàn bộ nhánh auto-skip theo token.
