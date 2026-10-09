# GPM Profile Lifecycle & Gmail DIE Retention Discipline

## 1. Bối cảnh & Nguyên tắc Bất biến (Hard Invariant)
- **Vấn đề thực tế**: Tài khoản Gmail được dùng để tạo profile GPM, đăng nhập, và sau đó được sử dụng để đăng ký / liên kết tài khoản **OpenAI, ChatGPT, Claude, Codex**. Quá trình này đã tốn chi phí thuê SIM xác minh số điện thoại (`5sim`, SMS OTP).
- **Hệ quả sai lầm**: Nếu script tự động kiểm tra thấy Gmail bị `DIE`, `BAN`, hoặc `SUSPENDED` mà tự động gọi API `profiles/delete/{pid}` thì **toàn bộ session, cookies, token và tài khoản OpenAI/Codex đã tốn tiền ver số sẽ bị xóa vĩnh viễn**.
- **Quy tắc bảo vệ tối cao**:
  - **CẤM TUYỆT ĐỐI** tự động xóa profile GPM khi Gmail gốc bị DIE.
  - Script lifecycle (`sync_gpm_lifecycle.py`) chỉ được phép tạo mới profile cho các Gmail `LIVE`, tuyệt đối không gọi `profiles/delete` đối với tài khoản DIE.

## 2. Quy chuẩn Cấu trúc Sổ cái Master (`master_gmail_manager.xlsx`)
- **16 cột chuẩn hóa**:
  1. `STT`
  2. `Email`
  3. `Password`
  4. `Recovery_Email`
  5. `2FA_Secret`
  6. `SDT` (Lưu số điện thoại từng dùng ver OTP/SMS)
  7. `Trạng Thái` (`LIVE`)
  8. `ChatGPT_Reg` (`YES`, `CHATGPT_READY`, hoặc trống)
  9. `Số Máy Farm`
  10. `Model Điện Thoại`
  11. `Serial Thiết Bị (Device ID)`
  12. `Proxy Đang Dùng`
  13. `Tên Profile GPM`
  14. `Nguồn`
  15. `Ghi Chú`
  16. `Cập Nhật`
- **Tách biệt dữ liệu vận hành vs lưu trữ**:
  - Các sheet hoạt động (`Master_All`, `Gmail_Dat`, `Kibe_Farm_S7`, `Admin_GPM_Pool`): Chỉ giữ lại 100% tài khoản `LIVE`.
  - Sheet `Gmail_DIE_Archive`: Lưu trữ toàn bộ tài khoản `DIE`, bảo toàn toàn bộ Email, Password, SĐT cũ, 2FA và Ghi chú để phục vụ tra cứu / khôi phục hoặc dùng cho các dịch vụ bên ngoài (OpenAI/ChatGPT).

## 3. Khôi phục Gmail Checkpoint SĐT & Dịch vụ 5sim
- **Hai dạng checkpoint Google khi đăng nhập môi trường mới**:
  1. **Dạng 1 — Xác nhận số điện thoại cũ (Confirm Phone Number)**: Google KHÔNG gửi mã OTP SMS, chỉ yêu cầu nhập lại số điện thoại đã lưu trong hồ sơ bảo mật để đối soát. Tra cứu ngay cột `SDT` trong `Gmail_DIE_Archive` (VD: `0563323349`) và điền vào để qua thẳng.
  2. **Dạng 2 — Bắt buộc nhận mã OTP SMS từ số mới (Anti-bot SMS checkpoint)**: Google cho phép nhập một số bất kỳ để nhận SMS. Sử dụng API `5sim` với sản phẩm `google` (Việt Nam ~$0.18, Indonesia/Philippines ~$0.08) để lấy số nhận OTP và mở khóa tài khoản.
