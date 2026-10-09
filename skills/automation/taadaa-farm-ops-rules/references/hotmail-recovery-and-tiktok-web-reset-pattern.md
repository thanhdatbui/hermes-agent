# Quy trình Cứu Hộ Hotmail & Reset Mật Khẩu TikTok Trên Thiết Bị Mới

## 1. Bối cảnh & Nguyên nhân gốc rễ
- **Lỗi đè pass ảo lúc reg (`social_reg_v1.py`):** Tài khoản TikTok đăng ký luồng email-only/OTP đôi khi không yêu cầu đặt mật khẩu. Nếu script tự ý gọi `make_tiktok_password(mail_pw)` ghi vào Excel, mật khẩu đó là pass ảo và TikTok sẽ báo sai mật khẩu khi đăng nhập lại trên thiết bị mới. User Rule 2026-08-16 bắt buộc: Không có pass thì để trống (`None` / `""`).
- **Cấm đặt pass đuôi cũ `@Ks`:** Mật khẩu TikTok mới bắt buộc dùng `generate_account_password()` (18 ký tự mạnh, ví dụ `CH1lDZ1du7JeqO-gjh`). Tuyệt đối cấm tự ý gõ pass có đuôi `@Ks`.
- **App Outlook Android trên S7 bị redirect sai:** Khi đăng nhập tài khoản Hotmail cũ trên App Outlook, Microsoft nhận diện thiết bị mới và tự động redirect vào luồng `Tạo tài khoản Microsoft mới (@outlook.com.vn)`. Không xuất hiện ô nhập pass hay link gửi mã OTP khôi phục.
- **Chrome Android (Web Login) ổn định hơn:** Trình duyệt Chrome xử lý OAuth / form `login.live.com` chuẩn xác, cho phép click vào dòng `Gửi mã đến th*****@gmail.com` để giải cứu.
- **App TikTok chặn Reset Password trên thiết bị mới:** Khi vào App TikTok > "Bạn cần trợ giúp đăng nhập?" > "Đặt lại mật khẩu bằng email" > nhập OTP, máy chủ TikTok nhận diện thiết bị lạ và đá văng về màn hình đăng nhập hoặc FAQ. Phải mượn giao diện Web Chrome (`tiktok.com/login/email/forget-password`) để nhập OTP và đặt lại mật khẩu mới.

---

## 2. Quy trình thực thi chuẩn (Step-by-step)

### Bước 1: Khôi phục hộp thư Hotmail qua Gmail khôi phục (nếu sai pass mail)
1. Mở Chrome trên thiết bị vào `https://login.live.com`.
2. Điền địa chỉ Hotmail. Nếu Microsoft báo sai mật khẩu hoặc đòi xác minh, tìm link:
   `Gửi mã đến th*****@gmail.com`.
3. Điền email khôi phục `thanhdatbui1995@gmail.com` và bấm **Gửi mã**.
4. Dùng IMAP (`imap.gmail.com:993` với `OTP_MAIL_USER` và `OTP_MAIL_APP_PASSWORD`) đọc thư từ `account-security-noreply@accountprotection.microsoft.com` để lấy mã OTP 6 số.
5. Điền OTP vào Chrome > Bấm Back nếu hiện popup passkey > Chọn **Có** ở màn hình `Duy trì đăng nhập?`.
6. Xác nhận đã vào được hộp thư `https://outlook.live.com/mail/0/inbox`.

### Bước 2: Kích hoạt Quên mật khẩu TikTok qua Web Chrome
1. Mở Chrome truy cập thẳng: `https://www.tiktok.com/login/email/forget-password` (hoặc mở ẩn danh nếu đang dính session đăng nhập cũ).
2. Nhập địa chỉ Hotmail của nick cần reset > Bấm **Gửi mã**.
3. Chuyển sang tab Outlook đang mở sẵn (hoặc gọi Graph API nếu nick có token) để đọc mã OTP TikTok gửi về.
4. Điền mã OTP vào web TikTok.

### Bước 3: Đặt mật khẩu mới chuẩn farm (CẤM đuôi `@Ks`)
1. Sinh mật khẩu chuẩn bằng hàm:
   ```python
   from core.passwords import generate_account_password
   new_pw = generate_account_password(18)
   ```
2. Nhập mật khẩu mới vào form và bấm **Đăng nhập**.
3. Đồng bộ ngay mật khẩu mới vào toàn bộ các file Excel:
   - `taikhoan_dat_v2_updated .xlsx` (cột PASS)
   - `taikhoan_run_safe.xlsx`
   - `TikX.xlsx` tương ứng.

### Bước 4: Đăng nhập vào App TikTok
1. Mở App TikTok native (`com.ss.android.ugc.trill`).
2. Vào Hồ sơ > Thêm tài khoản > Đăng nhập > Email/Username.
3. Nhập Email/Username + Mật khẩu mới vừa đặt (kèm OTP email nếu TikTok yêu cầu lần đầu).
4. Xác nhận profile đã hiển thị đúng trên app.
