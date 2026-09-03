# Hotmail Password Reset & Recovery Workflow via Gmail (2026-08-21)

## 1. Tổng quan & Bản chất
- **App Outlook không hỗ trợ đổi mật khẩu/bảo mật native**: Bắt buộc thực hiện qua trình duyệt Web (Chrome trên máy farm có gán Proxy riêng).
- **Khi tài khoản bị sai mật khẩu hoặc cần đổi pass dứt điểm**: Luồng khôi phục qua `account.live.com/password/reset` là luồng chuẩn, sạch và ổn định hơn luồng đổi pass từ session đăng nhập cũ (tránh được bẫy re-auth danh tính O365 / Account Chooser loop).

---

## 2. Quy trình Chuẩn từng bước (Step-by-Step)

### Bước 1: Khóa màn hình dọc & Mở Chrome
```bash
adb -s <serial> shell settings put system accelerometer_rotation 0
adb -s <serial> shell settings put system user_rotation 0
adb -s <serial> shell am force-stop com.android.chrome
adb -s <serial> shell am start -a android.intent.action.VIEW -p com.android.chrome -d "https://account.live.com/password/reset"
```
*Lưu ý cốt tử:* CẤM để xoay ngang (landscape) vì sẽ làm trôi/khuất các nút "Tiếp theo", "Nhận mã", "Lưu" và bàn phím ảo che mất form.

### Bước 2: Nhập tài khoản Hotmail
- Chạm vào ô nhập liệu ("Email, điện thoại hoặc tên Skype") -> Gõ email Hotmail target -> Bấm nút **"Tiếp theo"** (màu xanh dương).
- Nếu gặp pop-up *"Sử dụng mật khẩu đã lưu?"* của Google Autofill -> Bấm phím Back (`keyevent 4`) để đóng pop-up trước khi tap nút.

### Bước 3: Xác nhận Email Khôi phục & Gửi mã OTP
- Màn hình chuyển sang: *"Chúng tôi cần xác nhận định danh của bạn"* với tùy chọn *"Gửi email đến th*****@gmail.com"*.
- **Quy tắc nhập email khôi phục:**
  - Tại form này, phía sau ô nhập ĐÃ CÓ sẵn đuôi `@gmail.com` cố định -> **CHỈ NHẬP PREFIX:** `thanhdatbui1995` (KHÔNG gõ thêm đuôi `@gmail.com`).
  - Bấm nút **"Nhận mã"** màu xanh dương.

### Bước 4: Đọc OTP tự động từ Gmail & Nhập mã
- Microsoft gửi email tiêu đề: *"Đặt lại mật khẩu tài khoản Microsoft cá nhân"* về `thanhdatbui1995@gmail.com`.
- Chạy script IMAP đọc mã OTP:
```python
from flows.hotmail_recovery import poll_latest_otp
code, subject, sender = poll_latest_otp(not_before_ts=time.time() - 300, timeout=30)
```
- **Bẫy LinkId 521839:** Luôn lọc bỏ chuỗi `521839` (LinkId chính sách của Microsoft) để không lấy nhầm mã OTP.
- Nhập mã 6 số vào ô *"Nhập mã"* -> Bấm nút **"Tiếp theo"**.

### Bước 5: Đặt Mật khẩu mới & Xác nhận
- Màn hình chuyển sang: *"Đặt lại mật khẩu của bạn"*.
- Nhập mật khẩu mới vào cả 2 ô: **"Mật khẩu mới"** và **"Nhập lại mật khẩu"** (chuẩn: chữ hoa, chữ thường, số, độ dài >= 12 ký tự, ví dụ `Taadaa2026M<so_may>`).
- Bấm nút **"Tiếp theo"**.
- Màn hình xác nhận thành công hiển thị: **"• Mật khẩu của bạn đã thay đổi"** hoặc **"Thông tin bảo mật được cập nhật"** kèm nút *"Đăng nhập"*.

### Bước 6: Cập nhật Workbook & Dọn dẹp
1. Ghi mật khẩu mới vào Cột 3 (Pass mail) và `thanhdatbui1995@gmail.com` vào Cột 5 (Mail KP) trong `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
2. Tự động lưu bản backup `.backup_after_...xlsx`.
3. Đóng Chrome (`am force-stop`), đưa máy về HomeScreen.
4. **Giữ nguyên Lock:** Duy trì file lock trong `~/.codex/device-locks/` cho đến khi user chỉ đạo nhả lock.
