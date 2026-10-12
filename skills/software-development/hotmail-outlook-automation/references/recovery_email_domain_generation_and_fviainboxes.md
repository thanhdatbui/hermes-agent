# Quy tắc Mail Khôi Phục Cho Tài Khoản Hotmail Nuôi & Bán (Recovery Email Domain & Fviainboxes)

## 1. INVARIANT USER PREFERENCE & BẢO MẬT TÀI SẢN
- **CẤM TUYỆT ĐỐI gán email cá nhân của User (`thanhdatbui1995@gmail.com`) vào các tài khoản Hotmail/Gmail thương phẩm.**
- **Lý do:** Tài khoản Hotmail sau khi nuôi và liên kết các nền tảng (TikTok, ChatGPT, Codex) sẽ được xuất bán cho khách hàng. Nếu gán email cá nhân của User:
  1. Khách hàng không thể nhận mã OTP để đăng nhập hoặc đổi mật khẩu sau này.
  2. Bị lộ email và thông tin cá nhân của User cho bên thứ ba.
- **Quy tắc bắt buộc:** Mọi tài khoản Hotmail cần thêm/đổi mail khôi phục thương phẩm **BẮT BUỘC** phải tự động tạo địa chỉ mail domain ảo có API đọc OTP công khai.

## 2. ĐỊNH DẠNG MAIL DOMAIN THƯƠNG PHẨM (CHUẨN SHOP & FARM)
- **Domain sử dụng:** `@fviainboxes.com` (hoặc `@smvmail.com`).
- **Quy tắc sinh email khôi phục mới:**
  `<username_hotmail><3_ky_tu_ngau_nhien>@fviainboxes.com`
  - *Ví dụ mẫu trong hệ thống:*
    - `tamaiischester@hotmail.com` -> `tamaiischester84x@fviainboxes.com`
    - `chasdanyell368@hotmail.com` -> `chasdanyell3682ia@fviainboxes.com`
    - `rencotonejcp238@hotmail.com` -> `rencotonejcp2389kz@fviainboxes.com`

## 3. CƠ CHẾ ĐỌC OTP TỰ ĐỘNG CỦA FVIAINBOXES (KHÔNG CẦN TẠO TÀI KHOẢN)
- `fviainboxes.com` là dịch vụ email tạm thời có public API dạng REST, không cần đăng ký hay tạo tài khoản trước:
  - **Endpoint danh sách thư:**
    `GET https://fviainboxes.com/messages?username={username}&domain=fviainboxes.com`
  - **Endpoint chi tiết thư:**
    `GET https://fviainboxes.com/message?username={username}&domain=fviainboxes.com&id={id}`
- **Module canonical của Farm:** `D:/Taadaa/Hotmail/scripts/mail_domain_otp_helper.py`
  - Hàm `get_otp_from_fviainboxes(recovery_email, timeout_seconds=40)` tự động poll danh sách thư và bóc mã OTP Microsoft 6 hoặc 7 chữ số.
- **Ưu điểm khi bàn giao cho khách:**
  - Khách nhận file định dạng 5 trường: `mail|pass|refresh_token|client_id|mail_recovery`.
  - Khách chỉ cần truy cập web `https://fviainboxes.com`, nhập phần username trước `@` là đọc được thư xác minh Microsoft ngay lập tức.

## 4. XỬ LÝ LÔ HÀNG HOTMAIL ZIN TRẮNG (BOXTAIKHOAN / SHOPCLONE7)
- **Phân loại nguồn hàng BoxTaiKhoan:**
  - **Lô có sẵn mail khôi phục (giá rẻ ~167đ):** Shop xuất đủ 5 trường kèm mail `@fviainboxes.com`.
  - **Lô Hotmail Zin trắng 100% (giá ~393đ - như lô tháng 8/2026):** Shop xuất đúng 4 trường `mail|pass|refresh_token|client_id`, chưa từng gán mail khôi phục nào.
- **Pitfall chặn oan toàn bộ nick trong supervisor:**
  - Script `gpm_change_hotmail_security.py` trước đây kiểm tra cứng `rec_email = get_recovery_email(email)`, dẫn đến 62 nick Zin trắng đều bị đánh dấu `BLOCKED` oan vì nhầm tưởng nick bị thiếu thông tin.
  - **Giải pháp đúng:** Khi tài khoản là nick Zin chưa có recovery email trong DB/Excel:
    1. Tự động sinh địa chỉ mới `<username><random3>@fviainboxes.com`.
    2. Add địa chỉ này vào mục bảo mật Microsoft.
    3. Dùng `mail_domain_otp_helper.py` bóc OTP hoàn tất liên kết.
    4. Cập nhật địa chỉ vừa add vào cột D của `gmail_clean_v2.xlsx`.
