# GPMLogin Dual-Farm Architecture & Unified Hotmail Lifecycle (Kibe + Admin)

## 1. Nguyên Tắc Cốt Lõi Kiến Trúc (Invariant)
1. **GPMLogin Duy Nhất Trên Kibe**:
   - GPMLogin v3 (`127.0.0.1:19995`) CHỈ cài đặt và vận hành tập trung trên **máy Kibe**.
   - Máy Admin KHÔNG chạy GPM. Dữ liệu tài khoản của Admin (`D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`) là danh sách các tài khoản Hotmail đang nuôi trên cụm điện thoại M201-280.
   - Kibe bốc dần Hotmail của Admin để tạo profile GPM và đăng nhập trên Kibe qua đúng cổng proxy tương ứng của máy đó (`10008`–`10035`).

2. **Kỷ Luật 1 Cronjob Điều Phối Duy Nhất (No Window Spam)**:
   - CẤM TUYỆT ĐỐI tạo thêm cronjob riêng lẻ cho Admin (như `gpm-5profiles-supervisor-admin`). Việc đẻ nhiều cronjob chạy subprocess ngầm tần suất 5 phút sẽ gây xung đột lock, tốn tài nguyên và nháy cửa sổ console cướp focus của User khi đang chơi game/làm việc.
   - BẮT BUỘC hợp nhất vào duy nhất 1 cronjob: `gpm-5profiles-lifecycle-supervisor` (`341f42ae292c`, chu kỳ `*/5 * * * *`).
   - Entry point: `gpm_5profiles_supervisor_wrapper.py` chạy tuần tự:
     - **Bước 1**: Quét & xử lý tối đa 5 profile Farm Kibe (M1–80).
     - **Bước 2**: Quét & xử lý tối đa 5 profile Farm Admin (M201–280).

3. **CẤM Bypass Bước `HOTMAIL_LOGIN` Khi Có OAuth Token**:
   - **Quy trình bắt buộc**: `HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `WAIT_7D` -> `CHANGE_INFO` -> `DONE`.
   - **Vai trò của OAuth Refresh Token (Cột 9 Graph API)**: CHỈ dùng để bóc OTP tự động qua API khi đăng ký dịch vụ (ChatGPT, TikTok...), TUYỆT ĐỐI KHÔNG ĐƯỢC dùng để bỏ qua bước đăng nhập web mail.
   - Mọi tài khoản mới hoặc chuyển giao từ phone farm bắt buộc phải đăng nhập `login.live.com` trên profile GPM để lưu cookie và session sống, nuôi browser fingerprint an toàn trước khi sang giai đoạn tiếp theo.
