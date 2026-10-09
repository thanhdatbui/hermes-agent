# Sự Cố Liên Kết ChatGPT Sau Reg Gmail Thất Bại (19/09/2026)

## 1. Tóm tắt sự cố
- Báo cáo chuỗi ca trưa (`post-noon-chain-watchdog`): Reg Gmail thành công 7 máy, nhưng ChatGPT linked thất bại 0/7.
- Đối soát chi tiết $O(1)$ qua OCR ảnh và log:
  + 5 máy (M02, M04, M09, M23, M59): Văng ra màn hình Home hoặc gõ trượt email, báo lỗi *"Không chuyển sang màn hình OTP sau khi submit email"*.
  + 1 máy (M01): Kẹt ở trạng thái *"Đang nhận thư của bạn..."*, báo lỗi *"Không tìm thấy hoặc không lấy được mã OTP từ Gmail"*.
  + 1 máy (M54): Bị checkmail.live báo DIE ngay sau khi reg.

## 2. Các cạm bẫy kỹ thuật đã phân tích và khắc phục
1. **Home Screen Drop Trap (Blind-tap + Keyevent 4):**
   - Khi WebView Chrome đang load trên mạng proxy 4G, element input email chưa render.
   - Nhánh fallback `else:` mù quáng tap tọa độ và gọi `shell(..., "input", "keyevent", "4")` với mục đích ẩn bàn phím.
   - Khi chưa có bàn phím ảo, `keyevent 4` (KEYCODE_BACK) đóng Chrome và đẩy máy về màn hình chính (Home Launcher).
   - Khắc phục: Bỏ toàn bộ blind-tap khi trang chưa load, kiểm tra render input node trước khi gõ.
   - **Lưu ý Unit Test Mock Isolation**: Trong hook cần gọi trực tiếp `shell(..., "input", "text", ...)` và `shell(..., "input", "tap", "540", "200")` để ẩn bàn phím an toàn (tránh dùng `keyevent 4`). Tuyệt đối không import helper `human_type` / `hide_keyboard` từ `gmail_reg_v10` vì bên trong chúng gọi `gmail_reg_v10.shell`, làm bypass mock trong unit test và gọi thẳng ADB thật vào `dev1` gây timeout/hang 180s trong pytest.
2. **Playwright Lock Collision trên Host:**
   - 7 tiến trình chạy song song cùng dùng chung `USER_DATA = r"D:/Taadaa/GPM auto/checkmail_proxy_data"`.
   - Chromium crash hàng loạt: `BrowserType.launch_persistent_context: Target page, context or browser has been closed`.
   - Khắc phục: Cấp phát thư mục user data tạm độc lập theo PID và timestamp, tự động cleanup trong `finally:`.
3. **Gmail Initial Sync Delay:**
   - Gmail mới tạo cần 30s-50s để khởi tạo hòm thư. Timeout cũ 12 vòng (~18s) quá ngắn.
   - Khắc phục: Tăng lên 25 vòng (~50-60s), nhận diện chuỗi *"đang nhận thư"*, *"getting your messages"* và tự động swipe pull-to-refresh.
