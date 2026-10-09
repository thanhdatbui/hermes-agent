# Direct Email Signup ChatGPT on Android S7 (No-OAuth Flow)

## 1. Context & Root Cause
- **Vấn đề OAuth Google cũ**: Khi vừa reg Gmail trên Samsung S7, nếu dùng nút "Tiếp tục với Google" (OAuth SSO), Google đánh giá tài khoản non trẻ có hoạt động bất thường và kích hoạt `challenge/iap` (bắt xác minh số điện thoại SMS). Nếu không có số thật, tài khoản sẽ bị Google vô hiệu hóa (DIE).
- **Phát hiện quan trọng**: Nhập thẳng email vào form của ChatGPT (`chatgpt.com/auth/login?screen_hint=signup`), OpenAI hỗ trợ gửi mã xác minh 6 số (OTP) trực tiếp về hộp thư Gmail.
- **Bẫy redirect Google giả lập**: Nếu Chrome trên S7 có lưu cache session cũ hoặc tài khoản cũ, Chrome sẽ tự động bật Smart Lock/Credential Manager đề xuất tài khoản cũ, làm trang bị redirect sang Google OAuth. Cần `pm clear com.android.chrome` hoặc chọn "Sử dụng mà không cần tài khoản" (Chrome FRE dismiss).

## 2. Quy trình thực thi chuẩn trên thiết bị Android S7

### Bước 1: Chuẩn bị trình duyệt Chrome sạch
```bash
adb -s <serial> shell pm clear com.android.chrome
adb -s <serial> shell am start -n com.android.chrome/com.google.android.apps.chrome.Main -d "https://chatgpt.com/auth/login?screen_hint=signup"
# Chờ 3s, tap bỏ qua màn hình chào mừng của Chrome (Sử dụng mà không cần tài khoản)
# Tâm nút dismiss: [540, 1595] trên S7
```

### Bước 2: Nhập email đăng ký
1. Tap vào ô `Email address` (tâm `[540, 1315]`).
2. Gõ email qua `adb shell input text <email>`.
3. Ẩn bàn phím ảo: `adb shell input keyevent 4`.
4. Bấm nút "Tiếp tục" (tâm `[540, 1500]`).
5. Chờ 6s để OpenAI chuyển sang màn hình `auth.openai.com/email-verification`.

### Bước 3: Lấy mã xác nhận 6 số từ App Gmail trên S7
1. Mở App Gmail: `adb shell am start -n com.google.android.gm/.ConversationListActivityGmail`.
2. **Xử lý máy có nhiều tài khoản Google**:
   - Nếu máy S7 chứa nhiều tài khoản cũ, Gmail có thể mở hòm thư của tài khoản khác khiến không thấy thư OTP mới.
   - Mở Drawer menu: `adb shell input swipe 10 500 600 500 200`.
   - Bấm vào mục **"Tất cả hộp thư đến"** (tâm `[540, 355]`).
3. Vuốt kéo xuống để đồng bộ thư mới: `adb shell input swipe 500 400 500 1200 300`.
4. Mở email từ ChatGPT (thường ở dòng đầu tiên `[540, 620]`).
5. Trích xuất mã OTP 6 số từ nội dung:
   - Dùng script ATX dump: `dump_ui_atx.py <serial> out.xml`.
   - Tìm text regex: `r"Nhập mã xác minh tạm thời này để tiếp tục:\s*(\d{6})"`.
6. Buộc dừng Gmail để giải phóng tài nguyên: `adb shell am force-stop com.google.android.gm`.

### Bước 4: Điền mã OTP vào Chrome
1. Chuyển lại Chrome: `adb shell am start -n com.android.chrome/com.google.android.apps.chrome.Main`.
2. Tap ô nhập mã OTP (bounds `[48,1068][1032,1250]`, tâm `[540, 1100]`).
3. Gõ mã 6 số qua `adb shell input text <otp>`.
4. Ẩn bàn phím: `adb shell input keyevent 4`.
5. Bấm nút "Tiếp tục" (tâm `[540, 1302]`).

### Bước 5: Hoàn tất form "Bạn bao nhiêu tuổi?" (`auth.openai.com/about-you`)
- **Pitfall IME dồn chữ**: Bàn phím ảo Samsung IME có thể che ô Tuổi, dẫn đến gõ tên bị dính tuổi (ví dụ `Nguye24`).
- **Cách xử lý chuẩn**:
  1. Ẩn bàn phím trước: `adb shell input keyevent 4`.
  2. Tap ô Name (`[111,990][969,1062]`, tâm `[540, 1026]`).
  3. Gõ tên tiếng Anh không dấu: `adb shell input text Nguyen%sNgan%sHa`.
  4. Ẩn bàn phím: `adb shell input keyevent 4`.
  5. Tap ô Age (`[111,1182][969,1254]`, tâm `[540, 1218]`).
  6. Xóa ký tự cũ: `for i in range(10): adb shell input keyevent 67`.
  7. Gõ số tuổi: `adb shell input text 24`.
  8. Ẩn bàn phím: `adb shell input keyevent 4`.
  9. Bấm nút "Tiếp tục" (tâm `[540, 1698]`).

### Bước 6: Nghiệm thu GATE 6 bắt buộc
- Bấm nút "Tiếp tục" trên popup "Bạn đã hoàn tất".
- Mở sidebar bên trái: tap icon hamburger (tâm `[78, 321]`).
- **Điều kiện PASS**:
  1. OCR thấy tên người dùng (ví dụ: `Nguyen Ngan Ha`) và tag gói dịch vụ `Free`.
  2. **Biến mất hoàn toàn** nút "Đăng nhập / Log in".
  3. Chụp ảnh màn hình lưu `reports/chatgpt_verified_gate6.png` và gắn `MEDIA:<path>`.
