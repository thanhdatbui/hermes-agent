# Hotmail Password Root Cause Analysis & BoxTaiKhoan Order Audit (2026-10-10)

## 1. Kỷ Luật Điều Tra Sai Pass Hotmail (Chống Võ Đoán Sàn Đổi Pass)
- **Tiên đề:** Các sàn MMO (BoxTaiKhoan, CloneFBIG...) bán hàng loạt qua API và không bao giờ tự ý đổi mật khẩu các tài khoản đã bán.
- Khi gặp lỗi Hotmail sai mật khẩu trên Web/GPM, chỉ có **2 nguyên nhân kỹ thuật thực tế**:
  1. **Đã chạy luồng đổi pass nhưng lưu rớt:**
     - Script đổi thông tin/bảo mật (`gpm_change_hotmail_security.py`) sinh mật khẩu ngẫu nhiên trong RAM và submit lên Microsoft thành công ở Bước 3.
     - Bước ghi xuống Master Excel (`taikhoan_dat_v2_updated .xlsx`) và `gmail_clean_v2.xlsx` nằm ở Bước 4 sau khi xác minh lại.
     - Nếu quá trình xác minh bị timeout, crash trình duyệt, hoặc ngắt kết nối CDP/GPM, exception xảy ra và pass mới trong RAM mất vĩnh viễn, trong khi Excel vẫn giữ nguyên pass cũ từ lúc mua.
     - **Dấu hiệu nhận diện:** Khi bấm "Quên mật khẩu", Microsoft hiện rõ đã được gán email khôi phục chính chủ `th*****@gmail.com` (`thanhdatbui1995@gmail.com`).
     - **Giải pháp:** Sử dụng ngay luồng Password Reset tự động qua IMAP Gmail để thiết lập mật khẩu mới và đồng bộ 3 nơi.
  2. **Tài khoản mua dạng Graph API / OAuth token chỉ đọc OTP lúc reg TikTok:**
     - Lúc mua tài khoản (định dạng `email|pass|refresh_token|client_id`), module reg TikTok (`[otp-graph]`) chỉ dùng `refresh_token` để đọc OTP từ xa qua Microsoft Graph API.
     - Quá trình này **hoàn toàn không đăng nhập mật khẩu web trên Microsoft**.
     - Nếu chuỗi password bên bán bàn giao bị sai ngay từ đầu hoặc bóc tách chuỗi lệch, password sai này nằm trong Excel suốt nhiều tháng mà không ai phát hiện cho tới khi đưa vào luồng login GPM web.
     - **Dấu hiệu:** Không có email khôi phục chính chủ; Microsoft bắt điền form khôi phục thủ công (như trường hợp M66 `ruitalex240@hotmail.com`).

## 2. Quy Trình Khôi Phục Hotmail Đã Gán Mail Khôi Phục
- **Cổng Reset:** Điều hướng trực tiếp đến `https://account.live.com/password/reset` trên profile GPM (tránh rate-limit do submit sai pass nhiều lần ở trang login).
- **Quy trình:**
  1. Nhập email Hotmail cần khôi phục.
  2. Chọn phương thức xác minh qua email khôi phục `th*****@gmail.com`.
  3. Form yêu cầu điền phần ẩn: chỉ điền phần username trước domain (`thanhdatbui1995`), không điền cả `@gmail.com` vì bên cạnh ô input đã có sẵn text cố định `@gmail.com`.
  4. Lấy mã OTP từ Gmail qua IMAP (dùng `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD` trong Windows Registry).
  5. Nhập OTP và submit.
  6. Điền mật khẩu mới (ví dụ `Taadaa#Pass2026!<Machine>`).
  7. **Đồng bộ dữ liệu bắt buộc (Atomic 3-Way Sync):**
     - Master Excel: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (cột `PASS MAIL` - Cột 7).
     - Kho Gmail Clean V2: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
     - Supervisor State: `D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json`.

## 3. Tra Cứu Đơn Hàng BoxTaiKhoan
- **Cơ chế API:** BoxTaiKhoan (`boxtaikhoan.com`) chỉ hỗ trợ API lấy số dư (`/api/profile.php?api_key=...`) và mua hàng (`/ajaxs/client/product.php` action `buyProduct`). **API KHÔNG CÓ endpoint tra cứu lịch sử đơn hàng qua api_key.**
- **Tra cứu qua Web UI:**
  - URL quản lý đơn hàng: `https://boxtaikhoan.com/product-orders`
  - Tài khoản người dùng: `thanhdatbui1995`
  - Trên máy trạm của User, Profile Chrome `Profile 3` (tên Profile "đạt" - email `thanhdatbui1995@gmail.com`) đã lưu session/token đăng nhập của BoxTaiKhoan.
  - Có thể mở trực tiếp Profile 3 hoặc kết nối CDP vào Profile 3 để tra cứu đối soát đơn hàng cũ.
