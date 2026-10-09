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

## 3. Kiến Trúc Non-Blocking Device Lock & Khung Giờ Vàng (Cuốn Chiếu S7)
Khi tích hợp dọn tài khoản DIE tự động vào cron/watchdog định kỳ (như `sync_gpm_lifecycle.py`):

1. **Khung giờ Vàng (Golden Windows):**
   - Chỉ cho phép chạy dọn thiết bị S7 trong 2 cửa sổ đầu giờ:
     * Sáng: `07:15 - 08:15` (ngay sau khi checklive cập nhật Excel, trước khi chuỗi 2FA chạy lúc 08:30).
     * Trưa: `13:30 - 14:25` (trước chuỗi Reg Gmail 14:30).
   - Ngoài 2 khung giờ trên: bỏ qua thao tác dọn S7, chỉ dọn profile GPM trên máy tính.

2. **Quy trình Kiểm tra & Non-Blocking Lock Từng Máy:**
   - **Preflight ADB:** `adb -s <serial> get-state` phải trả về `device`. Nếu offline/unauthorized -> skip sang máy khác.
   - **Manifest Preflight:** Đọc manifest ngày hiện tại (`runtime/kibe/cron-state/manifests/<DATE>/assignment-v1-*.json`), đảm bảo máy không có ca nuôi đang chạy và không có lịch nuôi trong 30 phút tới.
   - **Non-blocking Device Lock:**
     * Gọi `acquire_device_lock(machine=str(mid), serial=serial, project="gpm-cleanup", bypass_proxy_readiness=True)`.
     * Bắt ngoại lệ `DeviceLockUnavailable`: Nếu máy đang bị giữ lock bởi cron nuôi TikTok hoặc cron khác -> **BỎ QUA NGAY LẬP TỨC (Skip & Continue)** để chuyển sang máy tiếp theo. Tuyệt đối không chờ mù quáng (blocking wait).
   - **Kiểm tra thực tế:** Dùng `dumpsys account` xác nhận email DIE thực sự còn trên máy trước khi gọi UI settings gỡ.
   - **Giải phóng nhanh:** Sau khi gỡ xong (hoặc lỗi), gửi `input keyevent 3` đưa máy về Home và thoát context lock để nhả thiết bị ngay lập tức trước khi sang máy kế tiếp.
