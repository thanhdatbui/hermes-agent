# Khôi phục tài khoản TikTok bị sai pass / lệch pass do lỗi reg cũ qua Web Reset & Hotmail

## 1. Nguyên nhân gốc rễ lỗi sai pass trên Phone Farm
- **Lỗi sinh pass ảo khi Reg:** Trong script reg cũ (`social_reg_v1.py`), hàm `ensure_profile_completed_and_track` có dòng fallback `tiktok_pw = tiktok_pw or make_tiktok_password(mail_pw)`. Khi TikTok bỏ qua bước tạo mật khẩu trong lúc reg (luồng OTP email), tài khoản trên server TikTok **chưa hề có mật khẩu**. Nhưng script lại tự sinh mật khẩu random ghi vào Excel.
- **Hệ quả:** Khi đăng nhập lại trên thiết bị mới, TikTok bắt xác minh danh tính bằng mật khẩu. Nhập mật khẩu trong Excel thì server TikTok báo: `Sai tài khoản hoặc mật khẩu`.

## 2. Quy tắc mật khẩu bắt buộc (User Rule)
- **TUYỆT ĐỐI CẤM** dùng mật khẩu có đuôi `@Ks` cũ (ví dụ `Susan123@Ks`).
- **BẮT BUỘC** dùng hàm `generate_account_password()` từ `D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/core/passwords.py` để sinh chuỗi mật khẩu mạnh 16-18 ký tự ngẫu nhiên (chứa chữ hoa, chữ thường, số, ký tự gạch ngang `-`).
- Khi reg tài khoản mới: Nếu TikTok không yêu cầu tạo pass, cột PASS trong Excel **BẮT BUỘC ĐỂ TRỐNG (`None` / `""`)**.

## 3. Luồng xử lý: App TikTok vs Chrome Web Reset
- **Hạn chế của App TikTok:** Trên thiết bị mới (Trust score = 0), khi bấm "Bạn cần trợ giúp đăng nhập?" -> "Đặt lại mật khẩu bằng email", sau khi điền OTP thì app TikTok thường đá văng về màn hình đăng nhập hoặc chuyển sang trang trợ giúp FAQ, không cho đặt mật khẩu mới.
- **Giải pháp qua Chrome Web:**
  1. Mở Chrome trên máy vào: `https://www.tiktok.com/login/email/forget-password` (hoặc mở thẻ ẩn danh nếu Chrome đang có session TikTok cũ).
  2. Điền email Hotmail -> Bấm "Gửi mã".
  3. Lấy mã OTP từ Hotmail (qua Microsoft Graph API nếu có OAuth Token, hoặc qua Chrome mở `outlook.live.com/mail/0/inbox`).
  4. Điền OTP vào web TikTok -> Nhập mật khẩu mới được sinh bằng `generate_account_password()`.
  5. Sau khi web TikTok báo đổi mật khẩu thành công: Mở App TikTok -> Nhập email -> Nhập OTP email -> Khi TikTok hiện màn hình "Xác minh danh tính: Nhập mật khẩu" -> Điền mật khẩu mới vừa đặt -> Đăng nhập thành công 100%.
  6. Đồng bộ ngay mật khẩu mới vào toàn bộ các file Excel liên quan: `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik*.xlsx`.

## 4. Cooldown và tránh Rate-limit
- Không spam thử liên tục khi TikTok báo lỗi hoặc chưa gửi mail.
- Chu kỳ thử lại an toàn cho Watchdog: Giãn cách 1h đến 6h (khung 6h là an toàn nhất để tránh khung dọn dẹp cache 01:00-04:50 sáng của farm).
