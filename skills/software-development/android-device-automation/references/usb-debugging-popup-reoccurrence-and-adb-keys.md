# USB Debugging Popup Reoccurrence & Whitelist Corruption (Samsung Android 8.0)

## Triệu chứng & Bối cảnh
Người dùng thắc mắc: *"Ủa t nhớ ở kibe t tắt cái này r mà sao h vẫn hiện"* hoặc *"Vấn đề là các máy này trc t từng bấm r tick cả luôn cho phép r sau 1 time lại bị lại"*.
Trên màn hình thiết bị Android (Samsung S7 / Android 8.0), hộp thoại `Allow USB debugging?` (`com.android.systemui/.usb.UsbDebuggingActivity`) xuất hiện trở lại dù trước đó đã từng tick "Luôn cho phép từ máy tính này" (*Always allow from this computer*).

## Nguyên nhân gốc rễ (Root Cause Analysis)

1. **Lỗi format / Rác trong file `adb_keys` trên thiết bị (`/data/misc/adb/adb_keys`)**:
   - File whitelist `adb_keys` phình to (>9-10 KB, tương đương >15 RSA keys tích tụ qua nhiều lần cắm nhiều máy tính/tool khác nhau).
   - Xuất hiện dòng trống hoặc corrupted key. Logcat của thiết bị ghi nhận rõ:
     ```text
     I/adbd: Loading keys from /data/misc/adb/adb_keys
     E/adbd: Invalid base64 key in /data/misc/adb/adb_keys
     I/adbd: Calling send_auth_request...
     D/UsbDebuggingActivity: onCreate use sec_always_use_checkbox
     ```
   - Khi daemon `adbd` parse file từ trên xuống dưới, đụng phải dòng lỗi base64 sẽ ngắt ngang, không đối chiếu tới khóa RSA của máy tính hiện tại, dẫn tới Android coi như máy tính chưa từng được whitelist và bắt buộc hiện lại popup.

2. **USB Flapping / Sụt áp cổng Hub USB**:
   - Khi hub USB sụt áp hoặc cắm rút chập chờn liên tục, thiết bị kích hoạt chuỗi sự kiện `USB disconnect` -> reconnect. Tiến trình `adbd` nạp lại auth. Nếu file `adb_keys` bị lỗi như trên, popup sẽ lập tức bung ra.

3. **Cơ chế thu hồi tự động của Samsung Knox / Smart Manager**:
   - Trên Android 8.0 Samsung, cơ chế bảo mật tự động thu hồi (revoke) các ủy quyền ADB không hoạt động lâu ngày hoặc khi danh sách khóa vượt ngưỡng.

## Giải pháp & Hướng xử lý từ PC

1. **Không thể tắt cơ chế bằng lệnh setting thông thường**:
   - Đây là cơ chế bảo mật cấp hệ điều hành (AOSP / Linux kernel), không có thuộc tính `settings put global ...` để tắt hoàn toàn trên ROM unroot.

2. **Nếu máy đang ở trạng thái `device` (kết nối ADB được)**:
   - Dùng script tự động dập popup (như hàm `dismiss_usb_debugging_dialog` trong `social_reg_v1.py`):
     - Tìm checkbox `com.android.systemui:id/always_use_checkbox` -> tap để tick chọn.
     - Tìm button `android:id/button1` (hoặc text "OK") -> tap để xác nhận.
     - Thao tác này ghi đè khóa RSA hợp lệ mới nhất vào cuối file `adb_keys`.

3. **Thao tác nhanh bằng công cụ chiếu màn hình (Sync Control)**:
   - Trên tool chiếu màn hình đa thiết bị (`放大安卓投屏` / Scrcpy sync), bật chế độ đồng bộ chuột (Sync Mode), tick chọn "Luôn cho phép" và nhấn "OK" trên 1 máy, lệnh sẽ broadcast đến toàn bộ các máy đang kẹt popup.
