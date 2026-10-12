# Quy tắc Mail Khôi Phục Domain Riêng & Tránh Mail Cá Nhân Cho Hotmail Bán

## 1. Nguyên Tắc Cốt Lõi (User Invariant)
- **TUYỆT ĐỐI KHÔNG GÁN MAIL CÁ NHÂN (`thanhdatbui1995@gmail.com`)**: Tài khoản Hotmail trên Farm sau này dùng để xuất bán cho khách hàng. Nếu gán email cá nhân làm mail khôi phục sẽ làm lộ thông tin cá nhân và gây rủi ro bảo mật nghiêm trọng.
- **BẮT BUỘC DÙNG MAIL DOMAIN RIÊNG (`@fviainboxes.com`)**:
  - Công thức sinh: `<username_clean><3_ky_tu_ngau_nhien>@fviainboxes.com`
  - Ví dụ thực tế: `tamaiischester@hotmail.com` -> `tamaiischester84x@fviainboxes.com`
  - Đảm bảo tính duy nhất, không trùng lặp và tương thích với API đọc OTP công khai.

## 2. Cơ Chế Đọc OTP Tự Động Cho @fviainboxes.com
- Domain `@fviainboxes.com` cung cấp API công khai, không cần đăng ký tài khoản trước:
  - Lấy danh sách thư: `GET https://fviainboxes.com/messages?username={username}&domain=fviainboxes.com`
  - Lấy chi tiết thư: `GET https://fviainboxes.com/message?username={username}&domain=fviainboxes.com&id={id}`
- Module xử lý chuẩn: `D:/Taadaa/Hotmail/scripts/mail_domain_otp_helper.py` (hàm `fetch_recovery_email_otp`).
- Khách hàng khi mua nick có thể truy cập thẳng vào `https://fviainboxes.com` gõ username để lấy OTP Microsoft.

## 3. Đối Soát Lô Hàng BoxTaiKhoan (SHOPCLONE7)
- **Lô Hotmail Zin (tháng 8/2026, giá ~393đ)**: File tải về chỉ có 4 trường (`mail|pass|refresh_token|client_id`). Đây là nick Zin trắng, chưa có mail khôi phục từ trước.
- **Lô Hotmail kèm mail phục hồi (tháng 9/2026, giá ~167đ)**: File tải về có đủ 5 trường với mail khôi phục `@fviainboxes.com`.
- Khi xử lý bảo mật cho lô Zin, script BẮT BUỘC phải tự động sinh mail domain `@fviainboxes.com` và nạp vào `gmail_clean_v2.xlsx`, không được đòi hỏi mail khôi phục cũ có sẵn.

## 4. Giao Diện Bảo Mật Mới Của Microsoft (proofs/manage/additional)
- Nút "Thêm một cách đăng nhập khác" hiện là `<button>` hoặc `div[role=button]`, không còn là thẻ `<a>`. Selector cần bao gồm:
  - `button:has-text('Thêm một cách đăng nhập khác')`
  - `div[role='button']:has-text('Thêm một cách đăng nhập khác')`
- Khi bấm nút, modal popup hiển thị 3 lựa chọn:
  1. Khóa bảo mật / PIN
  2. `button:has-text('Sử dụng ứng dụng')` / `Use an app` -> Cài đặt 2FA TOTP Authenticator
  3. `button:has-text('Gửi mã qua email')` / `Email a code` -> Thêm mail khôi phục `@fviainboxes.com`
- Khi đóng tab Chrome CDP: Cookie và phiên đăng nhập được lưu trên ổ đĩa trong thư mục User Data Profile, đóng tab KHÔNG làm mất session. Cần gọi `GET /json/close/{targetId}` sau mỗi tác vụ để dọn tab rác, tránh ngốn RAM.
