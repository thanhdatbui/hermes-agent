# User Rule 2026-08-16 & 2026-09-17: Cấm Fallback Tự Chế Pass Ảo Khi Reg TikTok

## 1. Bản chất sự cố
- Trong quá trình đăng ký tài khoản TikTok bằng Email/OTP, nhiều trường hợp app TikTok bỏ qua màn hình tạo mật khẩu mà cho vào thẳng Profile (luồng Email-Only / OTP signup).
- **Lỗ hổng nghiêm trọng:** Dù ở nhánh chính đã có User Rule: *"Nếu không có màn nhập pass thật thì để trống `tiktok_pw = ""`"*, nhưng tại hàm chung `ensure_profile_completed_and_track` (dòng 5538 `social_reg_v1.py`) lại còn sót dòng:
  ```python
  tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")
  ```
- Dòng code này tự động sinh ra một chuỗi mật khẩu random ngẫu nhiên rồi ghi đè vào cột `PASS` của file Excel `taikhoan_dat_v2_updated .xlsx`.
- **Hậu quả:** File Excel lưu mật khẩu đẹp nhưng trên server TikTok tài khoản này chưa từng có mật khẩu. Đến khi đăng nhập trên thiết bị mới, TikTok bắt xác minh bằng mật khẩu ➔ Nhập pass trong Excel bị báo `Mật khẩu sai` hoặc `Sai tài khoản hoặc mật khẩu`, dẫn đến nguy cơ sai pass hàng loạt tài khoản toàn farm khi bán cho khách!

## 2. Kỷ luật bắt buộc (Strict Invariant)
1. **Xóa bỏ hoàn toàn fallback:** Cột `PASS` trong Excel chỉ được ghi nhận giá trị khi và chỉ khi bước `fill_password_and_login` thực sự hoàn tất và trả về `True`.
2. **Ép để trống:** Nếu flow không qua màn tạo pass, `tiktok_pw` **BẮT BUỘC ĐỂ TRỐNG (`""` hoặc `None`)**.
3. **Quy trình đăng nhập lại cho nick phôi chưa có pass:**
   - Tuyệt đối không thử mò hay brute-force mật khẩu làm dính rate limit 30 phút.
   - Bắt buộc đăng nhập bằng mã OTP gửi về Email (Hotmail/Gmail).
   - Sau khi vào app bằng OTP, điều hướng vào `Cài đặt` ➔ `Tài khoản` ➔ `Mật khẩu` để **TẠO MẬT KHẨU LẦN ĐẦU**, sau đó mới lưu mật khẩu thật đó vào Excel.
