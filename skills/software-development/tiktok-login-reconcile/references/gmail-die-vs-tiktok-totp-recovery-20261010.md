# Bẫy Ngộ Nhận "Gmail DIE = Mất Nick TikTok" & Khôi Phục Bằng 2FA TOTP (2026-10-10)

## 1. Hiện Tượng Thực Tế (Case Study Nick `@anhdo829`)
- Nick `@anhdo829` (Lan Anh) thuộc Máy 20 (Tik 1 / Row 1), tạo ngày 04/03/2026 (> 7 tháng tuổi), đã đăng 21 video, 116 follow, 428 tim.
- Ngày 19/09/2026: Gmail liên kết `dotranganh221220002212@gmail.com` bị Google khóa (`gmail_die_tong.txt`).
- Ngày 28/08/2026: Batch reg tự động tạo nick mới `@javialdzxxj` trên Máy 20. Do app TikTok trên Android (Samsung S7) chạm giới hạn tối đa 8 tài khoản đăng nhập song song (`MACHINE_FULL_8_ACCOUNTS`), nick `@anhdo829` bị văng khỏi Account Switcher.
- Đến ca chạy, scheduler đọc workbook tìm `@anhdo829` nhưng không thấy trên máy nên phát sinh lỗi `ACCOUNT_MISSING`.
- **Sai lầm phổ biến**: Developer/Agent ngộ nhận Gmail die đồng nghĩa với nick TikTok die hoặc không thể cứu được, dẫn đến xóa nick khỏi Master workbook hoặc bỏ mặc nick bị đóng băng.

## 2. Nguyên Lý Bảo Toàn & Khôi Phục Tài Sản Farm
1. **Kiểm tra trạng thái Public Profile**:
   - Truy vấn TikTok public profile hoặc snapshot tracker: Nếu status vẫn `LIVE`, avatar vẫn hiện, video vẫn xem được -> Nick TikTok 100% còn sống.
2. **Quyền năng của 2FA TOTP (Authenticator App)**:
   - Nếu nick đã bật 2FA Authenticator (Secret Key lưu tại Cột E trong Excel Master hoặc DB) và có mật khẩu tĩnh (Cột D):
   - Luồng đăng nhập của TikTok Android:
     `Username / Phone / Email` -> `Password` -> `Màn hình 2FA Xác minh 2 bước`.
   - Tại màn hình 2FA, chọn **"Ứng dụng xác thực"** và nhập mã 6 số sinh từ Secret Key (dùng thư viện `pyotp.TOTP(secret).now()`).
   - 👉 **HOÀN TOÀN KHÔNG CẦN OTP GMAIL HOẶC TRUY CẬP HỘP THƯ GMAIL ĐÃ DIE!**
3. **Quy trình cứu nick bị văng**:
   - Không được ép đăng nhập vào máy đang đủ 8 nick (sẽ bị TikTok chặn `MACHINE_FULL_8_ACCOUNTS`).
   - Tìm máy có slot trống (< 8 nick) hoặc máy có nick non/clone bị die.
   - Dùng script login chuẩn:
     ```bash
     python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <MAY> --email <USERNAME> --ss
     ```
   - Sau khi login thành công vào app TikTok, vào mục *Hồ sơ -> Cài đặt & Quyền riêng tư -> Tài khoản -> Thông tin người dùng -> Email* để đổi/liên kết sang mail LIVE mới (Hotmail/Gmail sạch) hoặc gỡ mail cũ.
   - Gán lại folder video tiếp theo (`N+1.mp4`) để tiếp tục nuôi cày view.

## 3. Kỷ Luật Đối Soát & Vận Hành
- CẤM vứt bỏ thông tin tài khoản (Password, 2FA key, ngày sinh) khi chỉ có Gmail die.
- Mọi tài khoản có `>= 10` video, tuổi đời `> 30` ngày là tài sản có giá trị trust cao trong Phone Farm, bắt buộc phải ưu tiên bảo toàn và phục hồi.
