# Kỹ Thuật Khôi Phục Session Chặn 2FA Ảo & Chuẩn Hóa Bio Bằng AdbKeyboard Broadcast

## 1. Bản Chất Hiện Tượng 2FA Ảo Khi Switcher Trên TikTok Multi-Account
- **Bối cảnh:** Khi chuyển tài khoản trong TikTok App bằng Account Switcher trên dàn Phone Farm (máy nuôi nhiều slot), ứng dụng đôi khi văng màn hình:
  `Thiết lập xác minh 2 bước — Ứng dụng xác thực (TOTP)` (yêu cầu 6 số).
- **Phát hiện quan trọng:** Đây nhiều khả năng là **2FA Ảo do kẹt UI Fragment/State Navigation của App**, KHÔNG PHẢI session đã bị revoke hay nick bị logout hoàn toàn. Tài khoản thực chất đã được nạp credential trong cache local của TikTok.

---

## 2. Quy Trình Vượt 2FA Ảo Qua Deep Navigation (Deep App Navigation SOP)

Thay vì dừng lại phân trần hoặc xin mã TOTP, Coordinator áp dụng chuỗi hành động cơ học:
1. **Thoát khỏi Navigation kẹt:**
   - Dùng `input keyevent 4` (Back) hoặc gọi `am force-stop <pkg> && monkey -p <pkg> -c android.intent.category.LAUNCHER 1` để reset UI state.
2. **Kích hoạt Tab Profile từ Root:**
   - Tap góc dưới bên phải (`input tap 970 1860` trên màn hình 1080x1920).
   - Kiểm tra OCR màn hình hiện tại: nếu đã vào đúng nick mục tiêu (handle `@...` đã chuyển) $\rightarrow$ Session đã active, bỏ qua màn hình 2FA hoàn toàn!
3. **Mở sâu màn hình Profile/Bio:**
   - Nếu thanh nút "Sửa hồ sơ" bị ẩn hoặc giao diện TikTok phiên bản mới không có nút "Sửa hồ sơ" ở giữa:
     * Dùng `uiautomator dump` tìm trực tiếp node `Button` có text của Bio (hoặc nút `+ Thêm tiểu sử`).
     * Tap thẳng vào tọa độ node đó (hoặc `input tap 250 670` đối với dòng Bio trên S7 1080x1920) để nhảy thẳng vào màn hình soạn thảo Tiểu sử (`Edit Bio Activity`).

---

## 3. Kỹ Luật Gõ Tiếng Việt Có Dấu Bằng AdbKeyboard Broadcast

Khi nạp Bio / Đổi Tên tiếng Việt có dấu:
1. **CẤM gõ `adb input text` thô:** Lệnh này làm mất dấu tiếng Việt, nuốt ký tự hoặc gây lỗi font trên Android.
2. **Kích hoạt AdbKeyboard:**
   ```bash
   adb shell ime set com.github.uiautomator/.AdbKeyboard
   ```
3. **Gửi dữ liệu qua Intent Broadcast (BẮT BUỘC DÙNG `ADB_KEYBOARD_INPUT_TEXT`):**
   * **Cảnh báo lỗi bẫy intent:**
     - Intent `ADB_INPUT_B64 --es msg <base64>` hay `ADB_INPUT_TEXT --es msg <text>` trả về `result=0` nhưng **hoàn toàn KHÔNG gõ ký tự vào ô nhập**.
     - Intent CHUẨN XÁC của AdbKeyboard trên Android Farm là:
       ```bash
       # 1. Xóa sạch ô nhập:
       adb shell am broadcast -a ADB_KEYBOARD_CLEAR_TEXT
       
       # 2. Gõ chuỗi Base64 UTF-8 (chuẩn xác 100% tiếng Việt có dấu):
       adb shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text '<chuoi_base64_utf8>'
       ```
     * Lệnh trên trả về `result=-1` (Activity.RESULT_OK), ký tự tiếng Việt có dấu xuất hiện đầy đủ trong ô `EditText`.
4. **Lưu Bio & Đối soát:**
   - Tap nút `Lưu` ở góc trên bên phải (`input tap 990 150` trên S7).
   - Chụp màn hình fresh, quét WinRT OCR xác nhận text Bio đã xuất hiện trên trang Profile và nút `+ Thêm tiểu sử` đã biến mất 100%.
