# Root Causes & Solutions: ChatGPT Direct Registration trên Samsung S7 (Android 8) — 24/09/2026

## 1. Hiện tượng & Bối cảnh
- Chuỗi sau ca trưa: Tỷ lệ link ChatGPT bị fail 100% (0/8) dù Gmail vừa tạo thành công và đang live.
- Kiểm tra trực tiếp trên thiết bị (Máy 16, 22, 24, 13) phát hiện 5 bẫy kỹ thuật liên hoàn khiến toàn bộ flow bị kẹt hoặc dính lockout của OpenAI.

---

## 2. Các điểm nghẽn kỹ thuật & Giải pháp kiểm chứng thực tế

### A. Chính sách mật khẩu mới của OpenAI (Bắt buộc >= 12 ký tự)
- **Bẫy**: Tại màn hình "Tạo mật khẩu", OpenAI bắt buộc `Ít nhất 12 ký tự`. Mật khẩu reg của Farm thường chỉ có 10–11 ký tự (vd: `Dao$Zone608` = 11, `Win44@Tra7` = 10). Màn hình báo đỏ và nút Tiếp tục bị vô hiệu hóa.
- **Giải pháp**:
  ```python
  if len(pw_to_type) < 12:
      pw_to_type = f"{pw_to_type}@2026"
  ```
  Sau khi gõ pass: gửi `keyevent 4` để ẩn bàn phím, tap Tiếp tục `(540, 1812)`, và gửi tiếp `keyevent 4` để đóng popup "Lưu mật khẩu" của Chrome.

### B. Bẫy Gom Thread Gmail & Lỗi `max_check_attempts`
- **Bẫy**: App Gmail tự động nhóm thư OpenAI vào cùng 1 conversation thread. Do farm tắt Auto-sync, khi mở Gmail máy không tự kéo thư mới -> Script bốc nhầm mã OTP của ngày hôm trước / thư cũ. Nhập sai 3 lần khiến OpenAI kích hoạt rate-limit:
  `error_code: max_check_attempts` (*Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại*) -> Khóa phiên 15–30 phút.
- **Giải pháp**:
  1. Mở Gmail: `shell(serial, 'am', 'start', '-n', 'com.google.android.gm/.ConversationListActivityGmail')`.
  2. Bắt buộc vuốt làm mới Inbox: `shell(serial, 'input', 'swipe', '540', '800', '540', '1600', '400')` và sleep 2-3s.
  3. Bóc tách OTP từ node đầu tiên trên đỉnh Inbox (`bounds [24,423][1056,696]`), kiểm tra nhãn "Chưa đọc" hoặc timestamp mới nhất.

### C. Bàn phím ảo Samsung gây Layout Shift nút Submit lên (540, 762)
- **Bẫy**: Sau khi gõ email vào WebView Chrome, bàn phím ảo Samsung đẩy nút Tiếp tục từ đáy màn hình lên đúng `(540, 762)`. Nếu tap tọa độ cũ `(540, 1504)` sẽ tap trúng phím chữ **`g`**, khiến email bị nối thành `@gmail.comg` và báo lỗi "Email không hợp lệ".
- **Giải pháp**:
  - Tap thẳng tọa độ khi bàn phím mở: `tap(device_id, 540, 762, wait=1.0)`.
  - Kết hợp gửi Enter: `shell(device_id, "input", "keyevent", "66")`.

### D. Kẹt màn hình Tìm kiếm thư (Search Mode) trong Gmail
- **Bẫy**: Nếu phiên trước Gmail dừng ở ô Search, mở Gmail lên bàn phím ảo che hết thư. Bấm 1 lần Back hoặc tap góc chỉ đóng bàn phím mà chưa về Inbox.
- **Giải pháp**: Gửi Back kép có delay:
  ```python
  shell(device_id, "input", "keyevent", "4")
  time.sleep(0.5)
  shell(device_id, "input", "keyevent", "4")
  time.sleep(1.5)
  ```

### E. Màn hình About You (Bạn bao nhiêu tuổi?) & Nghiệm thu
- **Tọa độ chuẩn xác**:
  - Tap ô Họ và tên: `(540, 1026)`, gõ tên không dấu (vd: `Thuan`).
  - Gửi `keyevent 4` ẩn bàn phím.
  - Tap ô Tuổi: `(540, 1310)`, gõ tuổi (tính từ DOB).
  - Gửi `keyevent 4` ẩn bàn phím.
  - Tap nút Tiếp tục: `(540, 1798)`.
- **Màn hình nghiệm thu thành công**:
  - URL: `auth.openai.com/email-verification` hoặc text: `"Đã xác minh email: Email của bạn (...) đã được xác minh"`.
  - Điều hướng tiếp sang `https://chatgpt.com/` hiển thị màn hình chính ("Bạn đang làm gì vậy?").
