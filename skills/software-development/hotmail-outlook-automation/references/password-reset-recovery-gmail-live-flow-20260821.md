# Quy trình Khôi phục & Đặt lại Mật khẩu Hotmail qua Recovery Gmail (2026-08-21)

## 1. Khái quát luồng Reset Password qua Chrome

Khi tài khoản Hotmail bị sai mật khẩu hoặc cần đổi pass mà không thể đăng nhập trực tiếp:
- **Địa chỉ khởi tạo:** `account.live.com/password/reset`
- **Mục đích:** Bỏ qua mật khẩu cũ, định danh qua mail khôi phục `thanhdatbui1995@gmail.com` để đặt thẳng mật khẩu mới.

---

## 2. Các bước thực hiện chi tiết (Đã kiểm chứng thành công trên Máy 30)

### Bước 1: Khóa màn hình dọc (Portrait) & Khởi chạy Chrome
- **Bắt buộc khóa xoay dọc:**
  ```bash
  adb shell settings put system accelerometer_rotation 0
  adb shell settings put system user_rotation 0
  ```
- **Mở trang reset:**
  ```bash
  adb shell am force-stop com.android.chrome
  adb shell am start -a android.intent.action.VIEW -p com.android.chrome -d "https://account.live.com/password/reset"
  ```

### Bước 2: Nhập Email Hotmail mục tiêu
- Màn hình hiển thị: *"Khôi phục tài khoản của bạn"* -> Ô *"Email, điện thoại hoặc tên Skype"*.
- Focus vào ô text và gõ email Hotmail đầy đủ.
- Xử lý nếu có pop-up *"Sử dụng mật khẩu đã lưu?"* của Google: Bấm phím Back (`input keyevent 4`) để đóng pop-up.
- Bấm nút **"Tiếp theo"** (nút xanh dương).

### Bước 3: Xác minh Danh tính qua Recovery Gmail
- Màn hình hiển thị: *"Chúng tôi cần xác nhận định danh của bạn"* -> Tùy chọn: *"Gửi email đến th\*\*\*\*\*@gmail.com"*.
- **QUY TẮC NHẬP TẠI ĐÂY:** Do ngoài form đã có sẵn đuôi `@gmail.com` -> **CHỈ NHẬP PREFIX:** `thanhdatbui1995`.
- Bấm nút **"Nhận mã"** (hoặc "Gửi mã").

### Bước 4: Đọc OTP tự động qua IMAP & Nhập mã
- Script đọc OTP từ `thanhdatbui1995@gmail.com` qua `poll_latest_otp`:
  - **Lưu ý lọc bẫy mã:** Email của Microsoft có chứa LinkId `521839` trong footer điều khoản; hàm bóc tách phải dùng regex theo cụm từ (`(?:ma cua ban|code is|ma bao mat)[^\d]{0,20}(\d{6})`) và blacklist số `521839`.
- Màn hình chuyển sang: *"Xác minh danh tính của bạn"* (Ô *"Nhập mã"*).
- Gõ mã OTP 6 số vừa đọc -> Bấm nút **"Tiếp theo"**.

### Bước 5: Đặt Mật khẩu Mới & Hoàn tất
- Màn hình hiển thị: *"Đặt lại mật khẩu của bạn"*.
- Nhập mật khẩu mới vào 2 ô: *"Mật khẩu mới"* và *"Nhập lại mật khẩu"*.
- Đóng bàn phím (`input keyevent 4`), cuộn nhẹ nếu cần, và bấm nút **"Tiếp theo"**.
- **Dấu hiệu thành công:** Màn hình hiển thị:
  - *"• Mật khẩu của bạn đã thay đổi"*
  - Kèm nút *"Đăng nhập"*.

### Bước 6: Cập nhật Kho dữ liệu & Dọn dẹp
- Ghi mật khẩu mới vào cột 3 (`Pass mail`) và ghi `thanhdatbui1995@gmail.com` vào cột 5 (`Mail KP`) trong `gmail_clean_v2.xlsx`.
- Tạo file backup timestamped trước/sau khi ghi.
- Đóng Chrome, đưa thiết bị về HomeScreen (`input keyevent 3`).
- **GIỮ NGUYÊN DEVICE LOCK:** Giữ file lock trong `~/.codex/device-locks` để bảo vệ máy, không tự ý unlock khi chưa có lệnh từ người dùng.
