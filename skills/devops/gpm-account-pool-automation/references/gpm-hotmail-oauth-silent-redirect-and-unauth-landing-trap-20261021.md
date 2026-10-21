# Cạm Bẫy OAuth Silent Redirect & Nhận Diện Đăng Nhập Ảo (False-Done) Trên Microsoft Hotmail (2026-10-21)

## 1. Hiện Tượng Hiện Trường
Trong quá trình tự động đăng nhập Hotmail bằng mật khẩu trên GPMLogin (`batch_gpm_hotmail_password_login.py`), sau khi nhập email và password, trình duyệt chuyển qua URL trao đổi token ngầm:
`https://account.microsoft.com/auth/complete-client-signin-oauth-silent?state=...`

## 2. Các Cạm Bẫy Kỹ Thuật Nguy Hiểm
1. **Bẫy Ngắt Silent Sign-in bằng `page.goto`**:
   - Nếu script thấy URL `complete-client-signin` mà vội vã gọi `page.goto("https://account.microsoft.com")`, toàn bộ tiến trình trao đổi token ngầm qua iframe/script của Microsoft sẽ bị hủy ngay lập tức.
   - Trình duyệt bị văng về trang quảng bá vãng lai (Unauthenticated Promo Landing Page):
     - URL: `https://account.microsoft.com/account?pageName=Account`
     - Tiêu đề: `Microsoft account | Đăng nhập hoặc tạo tài khoản của bạn ngay hôm nay – Microsoft`
     - Nội dung: *"Hoàn toàn miễn phí với tài khoản Microsoft - Đăng nhập để quản lý tài khoản của bạn"*.
2. **Bẫy Selector Universal Header (UHF False Positive)**:
   - Trên trang Promo vãng lai, Microsoft vẫn hiển thị Universal Header (UHF) có icon tròn chứa chữ `ME`, nút `@Phản hồi`, và text `Tài khoản Microsoft`.
   - Nếu script kiểm tra auth dựa vào text `"Tài khoản Microsoft"`, `"@Phản hồi"`, avatar `#mectrl_headerPicture`, hay `netloc == "account.microsoft.com"` mà không loại trừ nội dung trang promo, script sẽ báo `LOGIN SUCCESS` giả tạo dù thực tế phiên đăng nhập chưa hề được thiết lập.

## 3. Giải Pháp & Quy Chuẩn Xử Lý Chuẩn Xác
1. **Chờ Tự Nhiên (Zero Force-Goto)**:
   - Khi gặp URL `complete-client-signin-oauth-silent`, tuyệt đối không gọi `page.goto`.
   - Chờ polling 1s (tối đa 15-20s) để Microsoft tự hoàn tất silent signin và tự động chuyển hướng về trang chủ:
     `https://account.microsoft.com/?lang=...` với tiêu đề `Microsoft account | Trang chủ`.
2. **Bộ Lọc Chặn False Positive Auth**:
   - **LOẠI TRỪ (Unauthenticated)**: Nếu DOM chứa một trong các cụm từ:
     - `"hoàn toàn miễn phí với tài khoản microsoft"`
     - `"đăng nhập để quản lý tài khoản của bạn"`
     - `"sign in to manage your account"`
     -> Đánh dấu `logged_in = False` ngay lập tức.
   - **XÁC NHẬN (Authenticated)**: Chỉ công nhận thành công khi xuất hiện các thẻ quản trị thực tế của tài khoản cá nhân:
     - `"thay đổi mật khẩu"` / `"change password"`
     - `"bảo mật"` / `"security"`
     - Tiêu đề trang chứa `"trang chủ"` hoặc `"home"`.
3. **Thử Thách Xác Minh Danh Tính (OTP Mail Khôi Phục `@fviainboxes.com`)**:
   - Khi gặp challenge *"Sắp hoàn thành / Almost there - Gửi mã đến ..."*, tự động tra cứu recovery email tương ứng trong `gmail_clean_v2.xlsx`, điền email, gửi mã và gọi `fetch_recovery_email_otp` từ `mail_domain_otp_helper.py` để polling OTP và submit.
   - Tuyệt đối không đưa các từ khóa challenge xác minh email vào `hard_block_keywords`.
