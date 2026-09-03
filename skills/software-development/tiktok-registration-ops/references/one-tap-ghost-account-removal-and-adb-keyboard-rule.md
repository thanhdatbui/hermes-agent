# One-Tap Ghost Account Removal & AdbKeyboard Standardization (2026-08-24)

## 1. Fast-Login / One-Tap Screen Ghost Account Removal
- **Hiện tượng:** Khi mở TikTok để reg tài khoản mới, app hiển thị màn hình One-tap login: "Tiếp tục với tên @<username_cũ>" (nhưng nick này không có trong Excel/tracking của máy, chỉ là cache rác).
- **Quy trình xử lý:**
  1. Kiểm tra UI XML nếu có "Tiếp tục với tên" / "Xóa tài khoản":
  2. Bấm menu 3 chấm góc trên bên phải (hoặc node `Xóa tài khoản` nếu hiển thị trực tiếp).
  3. Bấm xác nhận `Xóa` / `Delete` để giải phóng session rác.
  4. Bấm `Sử dụng tài khoản khác` ở dưới đáy màn hình để chuyển vào luồng đăng ký tài khoản mới sạch sẽ.

## 2. Chuẩn hóa Bàn phím AdbKeyboard (Cấm SamsungKeypad)
- **Vấn đề của SamsungKeypad:**
  - Không nhận tiếng Việt có dấu và ký tự đặc biệt qua broadcast `ADB_KEYBOARD_INPUT_TEXT`.
  - Làm rơi ký tự, gõ nhầm số máy hoặc ô input bị trống.
  - Gây dialog popup "Chọn bàn phím" che khuất nút hành động.
- **Quy chuẩn:**
  - Toàn bộ repo farm (`Tiktok_Reg`, `tiktok-log-in`, `Hotmail`, `add mail khoi phuc`, v.v.) BẮT BUỘC dùng:
    ```bash
    ime enable com.github.uiautomator/.AdbKeyboard
    ime set com.github.uiautomator/.AdbKeyboard
    am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64_encoded_text>
    ```
  - Package chuẩn: `com.github.uiautomator/.AdbKeyboard` (CẤM dùng nhầm `com.android.adbkeyboard`).
  - Duy nhất repo `register gmail` (`gmail_reg_v10.py`) giữ lại SamsungKeypad để bypass bot detection của Google Play Services.

## 3. Proxy Gate Bắt Buộc Trước Khi Reg
- Trước khi dispatch bất kỳ máy nào, bắt buộc kiểm tra:
  ```bash
  am broadcast -a vn.vichanger.app.GET_IP
  ```
- Điều kiện PASS: `result=200` VÀ `IP != '1.53.114.53'` (IP trực tiếp của farm). Máy nào timeout hoặc result=0/mất proxy phải loại ngay khỏi danh sách chạy.

## 4. Banner Đỏ & Giữ Lock Khi Báo Cáo Máy Lỗi
- Mọi ảnh màn hình lỗi gửi user bắt buộc gắn Banner đỏ đầu ảnh: `[MAY X] - HH:MM:SS dd/mm`.
- Máy gặp sự cố BẮT BUỘC giữ nguyên màn hình hiện trường và giữ lock thiết bị, CẤM tự ý `force-stop` hoặc bấm về `HOME`.
