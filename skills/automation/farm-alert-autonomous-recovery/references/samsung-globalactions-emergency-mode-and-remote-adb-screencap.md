# Samsung GlobalActions, Emergency Mode & Remote ADB Screencap Pitfalls

## 1. Dismissing Stuck System Dialogs & Power Menu O(1)
Khi Samsung S7 rơi vào trạng thái kẹt `mCurrentFocus=Window{... u0 Tùy chọn thiết bị}` (GlobalActions menu: Tắt nguồn, Khởi động lại, Chế độ khẩn cấp) hoặc màn hình điều khoản `com.sec.android.emergencymode.service` (CHẾ ĐỘ KHẨN CẤP):
- Nhấn phím `Back` (keyevent 4) hoặc `Home` (keyevent 3) thường không đóng được triệt để hoặc bị DimLayerController đè đen màn hình (`SurfaceView` bị ẩn).
- **Lệnh giải phóng O(1) chuẩn Android:**
  ```bash
  adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS
  ```
  Lệnh này đóng toàn bộ system dialog, power menu, notification shade ngay lập tức mà không cần tap tọa độ hay can thiệp thủ công.

## 2. Lỗi Corrupted PNG khi Screencap trên Git Bash / MSYS Windows
- **Hiện tượng:** Chạy `adb exec-out screencap -p > file.png` sinh ra file khoảng 12KB - 13KB, PIL mở ra báo 1 màu đen hoặc ảnh bị hỏng/lệch cấu trúc PNG.
- **Nguyên nhân:** Shell MSYS / Git Bash trên Windows tự động chuyển đổi ký tự xuống dòng `\n` thành CRLF `\r\n` trên luồng stdout redirection (`>`), phá hủy nhị phân PNG stream.
- **Giải pháp bắt buộc:** Chụp vào bộ nhớ trong máy rồi pull nhị phân sạch:
  ```bash
  adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png /path/to/local.png
  ```

## 3. False Positive "Login Detected" từ TikTok Rewards Widget
- Widget sự kiện tích điểm / nhiệm vụ thưởng trên For You feed (ví dụ: `Nhập ngay có thưởng` kèm icon quà và nút đóng `x`) thường chứa cụm từ `Nhập ngay`.
- Các bộ lọc token nhạy cảm nếu đối soát sơ sài từ khóa `nhập` hoặc OCR nhầm thành `đăng nhập` sẽ kích hoạt báo động giả "login/account screen detected" làm hoảng loạn batch.
- **Cách đối soát:**
  1. Kiểm tra database/Excel SoT (`taikhoan_run_safe.xlsx`, `tiktok_tracker_report.xlsx`) xác nhận trạng thái tài khoản LIVE.
  2. Dump UI XML qua `atx-agent curl` hoặc trích xuất cụ thể tọa độ box `[0, 300, 500, 700]` để xác nhận widget chiến dịch trước khi kết luận mất phiên.

## 4. Remote ADB Host (`192.168.110.119:5037`) & Python Runner
- Khi chạy script Python tương tác cụm Admin Remote từ máy Kibe:
  - Cần export biến môi trường: `ADB_HOST=192.168.110.119`.
  - Không dùng `adb forward tcp:7912 tcp:7912` qua LAN vì port forward được bind trên localhost của máy host remote (`192.168.110.119`), gây lỗi `URLError WinError 10061 Connection Refused` khi Kibe kết nối `127.0.0.1:7912`.
  - Bắt buộc dùng cơ chế device-local `atx-agent curl`:
    ```bash
    adb shell "/data/local/tmp/atx-agent curl -X POST --data '{\"jsonrpc\":\"2.0\",\"id\":\"1\",\"method\":\"dumpWindowHierarchy\",\"params\":[false]}' http://127.0.0.1:7912/jsonrpc/0"
    ```
