# Hotmail & 5SIM Codex Verification Lifecycle Architecture (2026-09)

## 1. Phân Tách 2 Nhánh Hotmail (Token vs Không Token)
- **Nhánh có OAuth Token (Graph API / refresh_token):**
  - **CẤM TUYỆT ĐỐI** ép đăng nhập `HOTMAIL_LOGIN` lên web `login.live.com` qua proxy GPM. Việc mở webmail bằng mật khẩu qua IP proxy mới sẽ kích hoạt Microsoft security checkpoint ("Verify your email" / đòi mail khôi phục).
  - Profile GPM mở thẳng `chatgpt.com` để chạy `CHATGPT_REG`.
  - Khi OpenAI gửi mã xác thực 6 số về Hotmail, runner PC dùng Microsoft Graph OAuth token bốc OTP trực tiếp qua API trong 2s.
- **Nhánh chưa có OAuth Token:**
  - Bắt buộc phải chạy `HOTMAIL_LOGIN` trên GPM để vào webmail lấy OTP.
  - Nếu Microsoft đòi xác minh mail khôi phục dạng domain temp-mail công khai (ví dụ `@fviainboxes.com`): truy cập `https://fviainboxes.com`, điền prefix email và click "Get Email" để đọc hòm thư khôi phục trực tiếp từ web.

## 2. Quy Trình Kích Hoạt 5SIM Codex OAuth (Ver Số Phone)
- **Luôn giữ thời gian chờ SMS chuẩn 90s:**
  - Không được tự ý cắt giảm xuống 45s; mặc dù OTP thường về trong 5–25s, mạng di động một số quốc gia cần thời gian dài hơn để chuyển tiếp SMS quốc tế từ OpenAI.
  - Khi hết 90s không có OTP, gọi API `https://5sim.net/v1/user/cancel/{order_id}` để hủy số và được hoàn lại 100% tiền vào balance ngay lập tức (không mất phí).
- **Cơ chế Live Pool Xoay Tua Đa Quốc Gia (`get_live_pool`):**
  - Không hardcode danh sách 1-2 quốc gia cố định khiến script bị dừng khi quốc gia đó tạm hết số.
  - Quét động qua API 5SIM theo mức giá trần ($\le \$0.15$), sắp xếp theo thứ tự:
    1. Ưu tiên Việt Nam (`virtual34`, `virtual47`) nếu có sẵn số.
    2. Fallback xoay vòng tự động theo tỷ lệ thành công cao nhất (`rate24`) của các nước giá rẻ: Hy Lạp (`virtual66`/`virtual34`), Anh (`virtual34`), Philippines (`virtual34`/`virtual58`), Thái Lan, Argentina (`virtual62`/`virtual34`).
  - Thiết lập số lượt thử liên hoàn $\ge 5$ lượt thử đa quốc gia trước khi kết luận BLOCKED.
- **Thao tác DOM Dropdown & Tel Input trên OpenAI:**
  - Dropdown Việt Nam: gõ `'Viet'` + `Enter`.
  - Sau khi chọn quốc gia xong, **bắt buộc gửi phím `Escape`** để đóng triệt để popover/dropdown overlay trước khi click và điền vào ô `input[type="tel"]` nhằm tránh lỗi pointer event interception.
  - Sử dụng `force=True` khi click và submit mã OTP.
