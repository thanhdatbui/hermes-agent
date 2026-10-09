# S7 Android 8 Account Cleanup & Preflight Check Live Pattern

## 1. Bối cảnh & Vấn đề
- Trên các máy Samsung Galaxy S7 (Android 8.0 / API 26), việc reg Gmail hoặc nuôi acc lâu ngày làm đầy slot tài khoản trên thiết bị (trần 5 acc Google).
- Nếu không gỡ các tài khoản DIE trước khi reg Gmail mới hoặc liên kết dịch vụ (ChatGPT, TikTok):
  1. Khi mở Chrome chọn Google OAuth, các tài khoản DIE/lạ che lấp danh sách Account Chooser, kích hoạt Google reCAPTCHA checkpoint ("Xác minh danh tính của bạn").
  2. Không còn slot để thêm tài khoản mới.
  3. Lệnh dump UI qua shell `/dev/tty` (`exec-out uiautomator dump /dev/tty`) trên Android 8.0 S7 trả về chuỗi rỗng hoặc bị kẹt `Killed 137`, khiến script gỡ tài khoản qua ADB bị timeout / fail.

## 2. Quy trình Preflight Check Live & Rolling Cleanup Chuẩn
File điều phối: `D:/Taadaa/GPM auto/scripts/preflight_s7_rolling_cleanup.py`.

### Bước 1: Quét danh sách & Check Live real-time
- Đọc danh sách tài khoản hiện có trên máy qua `dumpsys account`.
- Gọi trực tiếp module check live (`run_checkmail_kibe_farm.py` với Playwright headless/proxy) để kiểm tra trạng thái từng tài khoản.
- **Nếu phát hiện tài khoản `DIE`**: Đánh dấu ưu tiên gỡ ngay lập tức (`DIE_ACCOUNT_FOUND`), không cần đợi máy đủ 5 tài khoản.

### Bước 2: Thao tác gỡ tài khoản chuẩn trên Samsung S7 (Android 8.0)
1. Mở Cài đặt đồng bộ:
   ```bash
   am start -a android.settings.SYNC_SETTINGS
   ```
2. Kiểm tra nếu giao diện đang kẹt ở chi tiết tài khoản cũ (thấy nút `Đồng bộ tài khoản` hoặc `XÓA TÀI KHOẢN`):
   - Tap nút Trở về ở thanh header: tọa độ `(72, 144)`.
3. Nhận diện mục `Google`:
   - Dùng XML dump an toàn qua file trung gian `/sdcard/settings_dump.xml` (hoặc `get_ui_xml`).
   - Tap vào mục `Google` để mở danh sách tài khoản Google.
4. Tìm và tap vào email mục tiêu cần gỡ:
   - Nếu không thấy ở trang đầu, thực hiện vuốt nhẹ: `input swipe 540 1500 540 600 300`.
5. Bấm nút gỡ:
   - Trên Samsung S7, nếu có nút `XÓA TÀI KHOẢN` trực tiếp dưới màn hình thì tap thẳng.
   - Nếu không, tap menu 3 chấm góc trên bên phải `(1000, 150)` và chọn `Xóa tài khoản`.
   - Xác nhận tại popup: tap nút `XÓA TÀI KHOẢN` / `Remove account` tại tọa độ `(782, 1145)`.
6. Đưa máy về màn hình chính: `input keyevent 3`.

### Bước 3: Ghi nhận lịch sử tài khoản DIE
Mỗi tài khoản DIE sau khi gỡ thành công bắt buộc append vào:
`D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`
Định dạng: `<email_die>|<machine_id>|<serial>|<YYYY-MM-DD HH:MM:SS>`
Giúp các script đồng bộ dữ liệu (`gmail_clean_v2.xlsx`) đối soát và purge sạch tài khoản chết tự động.
