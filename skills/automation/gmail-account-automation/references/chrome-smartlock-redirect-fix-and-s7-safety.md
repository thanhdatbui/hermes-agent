# Khắc phục triệt để bẫy Google Smart Lock / Chrome Sign-in Redirect & Bẫy Xóa Cache Chrome S7

## 1. Nguyên nhân hiện tượng bị cưỡng chế chuyển hướng (Redirect) về Google OAuth
Khi mở link đăng ký trực tiếp của ChatGPT (`https://chatgpt.com/auth/login?screen_hint=signup`) trên Chrome điện thoại Samsung S7, dù đã nhập thẳng email và bấm Tiếp tục nhưng trình duyệt vẫn bị nhảy sang màn hình Google OAuth (`accounts.google.com/v3/signin/identifier`):
- **Cơ chế Google Smart Lock / Credential Manager**: Chrome trên Android tự động quét tài khoản Google đang có trên máy (hoặc tài khoản từng đăng nhập Chrome trước đó).
- Khi submit form đăng ký, Chrome kích hoạt popup *"Đăng nhập vào Chrome bằng tài khoản của <Tên>* hoặc âm thầm gợi ý tài khoản Google đồng bộ, dẫn tới việc request bị intercept và ép redirect về Google SSO.

## 2. Giải pháp làm sạch Chrome cô lập (Isolate Chrome)
Để chặn triệt để popup và cơ chế Smart Lock của Chrome:
```bash
# Xóa sạch dữ liệu Chrome (cookies, history, Google Smart Lock session)
adb -s <serial> shell pm clear com.android.chrome

# Mở lại Chrome với link ChatGPT
adb -s <serial> shell am start -n com.android.chrome/com.google.android.apps.chrome.Main -d "https://chatgpt.com/auth/login?screen_hint=signup"

# BẮT BUỘC: Xử lý First Run Experience (FRE) của Chrome
# Bấm nút "Sử dụng mà không cần tài khoản" (Dismiss FRE button)
# Bounds thường gặp: [72,1523][1008,1667] hoặc [72,1728][1008,1872] -> tap tâm (540, 1600 hoặc 540, 1800)
```

## 3. An toàn Dữ liệu khi `pm clear com.android.chrome`
- **Tài khoản Google trên Android S7**: Toàn bộ tài khoản Google quản lý trong Cài đặt Android (`dumpsys account`) **KHÔNG BỊ ẢNH HƯỞNG**. Xóa data Chrome không xóa tài khoản trên máy.
- **Tài khoản Hotmail / Outlook**:
  - Hotmail trên farm Taadaa được chạy và lưu session trong **App Outlook (`com.microsoft.office.outlook`)**.
  - `pm clear com.android.chrome` **HOÀN TOÀN KHÔNG CHẠM VÀO APP OUTLOOK**. Session Hotmail trong app Outlook giữ nguyên 100%.
  - *Lưu ý*: Chỉ những phiên web đăng nhập tạm bợ trên trình duyệt web Chrome mới bị logout.

## 4. Bẫy giao diện Form "Bạn bao nhiêu tuổi?" (`auth.openai.com/about-you`)
- Màn hình này gồm 2 trường: `name` (Họ và tên) và `age` (Tuổi).
- **Lỗi dồn chuỗi**: Trên màn hình dọc S7, bàn phím Samsung IME khi bật lên sẽ che khuất ô Tuổi. Nếu gửi lệnh nhập liên tiếp mà không ẩn bàn phím, cả tên và tuổi sẽ bị gõ dồn vào ô Tên (ví dụ `"Nguye24"`), còn ô Tuổi bị rỗng, dẫn đến lỗi đỏ *"Có vẻ thông tin không chính xác"*.
- **Cách xử lý chuẩn**:
  1. Ẩn bàn phím trước (`input keyevent 4`).
  2. Tap ô Tên (`[540, 1026]`) -> gõ tên không dấu -> ẩn phím (`keyevent 4`).
  3. Tap ô Tuổi (`[540, 1218]`) -> xóa rác 10 lần `keyevent 67` -> gõ số tuổi (ví dụ `24`) -> ẩn phím (`keyevent 4`).
  4. Cuộn màn hình hoặc tap nút "Tiếp tục" (`[540, 1698]`).
  5. Xử lý dialog onboarding cuối *"Bạn đã hoàn tất"* -> tap "Tiếp tục" (`[540, 1674]`).

## 5. Tiêu chuẩn Nghiệm thu Chống "Báo Cáo Láo" (Hard Verification)
- **CẤM NHÌN URL ĐOÁN MÒ**: URL `chatgpt.com` xuất hiện cả ở chế độ Khách vãng lai (Guest Mode).
- **Hard Assertions**:
  1. Mở menu thanh bên (`tap 78 321` trên S7) hoặc dump ATX UI XML.
  2. Phải tìm thấy tên người dùng (ví dụ `Nguyen Ngan Ha`), nhãn gói tài khoản `Free` (`radix-_r_... 'Nguyen Ngan Ha Free, mở menu hồ sơ'`).
  3. Tuyệt đối KHÔNG còn nút `"Đăng nhập"` / `"Log in"` ở góc trên bên phải hay trong thanh bên.
