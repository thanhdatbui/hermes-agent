# Quy trình Khôi phục & Đổi mật khẩu Hotmail qua Gmail khôi phục (2026-08-21)

## 1. Bản chất kiến trúc: Outlook App vs Chrome Mobile
- **Outlook App:** Chỉ là email client, không hỗ trợ giao diện đổi mật khẩu hay bảo mật nâng cao.
- **Thực hiện đổi pass / khôi phục:** Bắt buộc qua trình duyệt web Chrome trên thiết bị (được định tuyến qua proxy riêng của từng máy) tại:
  - `https://account.live.com/password/Change` (khi đã đăng nhập).
  - `https://account.live.com/password/reset` (khi tài khoản sai mật khẩu cần khôi phục qua email liên kết).

---

## 2. Quy tắc bắt buộc khi xử lý sự cố thiết bị (User Invariant)
- **Tuyệt đối không tự ý release lock khi đang fix máy:**
  - Giữ nguyên lease file lock trong `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` với cờ `release_on_terminal=False`.
  - Không unlock giữa chừng khi chưa có chỉ đạo từ user.
- **Khóa cứng xoay màn hình (Portrait Mode):**
  - Trước khi mở Chrome, bắt buộc tắt tự động xoay và khóa về chiều dọc:
    `adb shell settings put system accelerometer_rotation 0`
    `adb shell settings put system user_rotation 0`
  - Tránh để trình duyệt chuyển sang Landscape làm trôi nút bấm, che khuất form nhập và trơ focus.

---

## 3. Khác biệt giữa 2 Form xác nhận Email khôi phục của Microsoft
1. **Form Reset Password (`account.live.com/password/reset`):**
   - Đã có sẵn đuôi `@gmail.com` cố định bên ngoài ô input.
   - **Chỉ nhập prefix:** `thanhdatbui1995`. (Nếu nhập cả `@gmail.com` sẽ bị lỗi nhận diện).
2. **Form Security Proof khi đăng nhập (`login.live.com` - "Xác minh email của bạn"):**
   - Ô nhập liệu nhãn "Email" đang để trống hoàn toàn.
   - **Bắt buộc nhập đầy đủ:** `thanhdatbui1995@gmail.com`. (Nếu chỉ nhập prefix sẽ bị lỗi đỏ báo không trùng khớp).

---

## 4. Xử lý bóc tách mã OTP từ Gmail & Bẫy LinkId 521839
- Microsoft luôn đính kèm link điều khoản quyền riêng tư: `https://go.microsoft.com/fwlink/?LinkId=521839` trong email OTP.
- **Bẫy:** Regex tìm số 6 chữ số generic sẽ bắt nhầm `521839` thay vì OTP thật.
- **Xử lý chuẩn (`flows/hotmail_recovery.py`):**
  - Ưu tiên bắt theo mẫu cụm từ: `(?:ma cua ban|code is|ma bao mat)[^\d]{0,20}(\d{6})`.
  - Loại bỏ hoàn toàn candidate `521839`.

---

## 5. Xử lý Opaque WebView trên Samsung Galaxy S7 (Android 8)
- Trên Chrome WebView, các trường nhập liệu và nút bấm thường không expose ra cây Accessibility Tree XML (`ui_xml` rỗng).
- **Cơ chế hoạt động:**
  - Nhận diện State qua URL và OCR hình ảnh.
  - Tương tác nhập liệu bằng `AdbKeyboard` (`ADB_INPUT_TEXT` / `ADB_INPUT_B64`) hoặc `input text`.
  - Sử dụng phím `Enter (keyevent 66)` hoặc tap vào tọa độ chuẩn hóa màn hình dọc để submit.

---

## 6. Nhận diện Marker thành công tiếng Việt & Cập nhật Dữ liệu
- **Markers thành công:**
  - `"• Mật khẩu của bạn đã thay đổi"` / `"mật khẩu của bạn đã thay đổi"`
  - `"thông tin bảo mật được cập nhật"`
- **Đồng bộ Workbook `gmail_clean_v2.xlsx`:**
  - Cập nhật Mật khẩu mới vào Cột 3.
  - Cập nhật Mail khôi phục `thanhdatbui1995@gmail.com` vào Cột 5.
  - Luôn tạo file backup timestamp: `gmail_clean_v2.backup_after_m<N>_change_info_<timestamp>.xlsx` trước khi ghi đè.
