# User Rule 2026-08-16 & Fix Triệt Để Ghi Pass Ảo (2026-09-17)

## 1. Gốc Rễ Lỗi Sai Pass Toàn Farm
- Trong luồng đăng ký TikTok bằng Email (`social_reg_v1.py`), nhiều khi TikTok cho vào thẳng Profile qua OTP mà không yêu cầu tạo mật khẩu.
- Khi đó biến `tiktok_pw` bị rỗng.
- Trước ngày 2026-09-17, tại hàm ghi tracking `ensure_profile_completed_and_track` (dòng 5538) tồn tại đoạn fallback tai hại:
  `tiktok_pw = tiktok_pw or (make_tiktok_password(mail_pw) if mail_pw else "")`
- Đoạn code này đã tự tiện sinh ra một chuỗi mật khẩu random ngẫu nhiên rồi ghi vào cột D (PASS) của file Excel, trong khi server TikTok chưa từng nhận pass này.
- Hậu quả: File Excel ghi pass rất đẹp, nhưng thực tế khi đăng nhập lại trên thiết bị mới thì TikTok báo thẳng: `Sai tài khoản hoặc mật khẩu`.

## 2. Invariant Cố Định (User Rule 2026-08-16)
- **Nếu flow KHÔNG có màn nhập mật khẩu thật hoặc TikTok skip tạo pass:** Cột `PASS` trong Excel BẮT BUỘC ĐỂ TRỐNG (`""` hoặc `None`).
- **CẤM TUYỆT ĐỐI:** Tự động sinh pass ảo hay fallback chế pass khi chưa được app xác nhận.

## 3. Quy Trình Cứu Nick & Đặt Pass Mới Đồng Bộ (2026-09-17)
1. Khi đăng nhập nick chưa có pass trên thiết bị mới, TikTok bắt xác minh OTP email + Nhập mật khẩu.
2. Vì chưa có pass, không thể nhập pass cũ.
3. Mở web Chrome trên thiết bị vào `https://www.tiktok.com/login/phone-or-email/email`.
4. Bấm **Bạn quên mật khẩu?** -> Chọn **Đặt mật khẩu bằng: Email**.
5. Nhập email nick -> Bấm **Gửi mã**.
6. Đọc OTP gửi về hộp thư Hotmail/Outlook.
7. Điền OTP vào web TikTok -> Nhập mật khẩu mới chuẩn (ví dụ `Susan123@Ks`).
8. Sau khi reset thành công trên web, mở app TikTok đăng nhập bằng mật khẩu mới + OTP email.
9. Đăng nhập thành công -> Cập nhật ngay mật khẩu thật mới này vào đồng loạt:
   - `taikhoan_dat_v2_updated .xlsx`
   - `taikhoan_run_safe.xlsx`
   - `TikN.xlsx`
