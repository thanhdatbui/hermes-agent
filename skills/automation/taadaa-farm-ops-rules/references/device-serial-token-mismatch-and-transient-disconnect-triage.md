# Triage Alert "Device serial 'device:<serial>' was not found in adb devices"

## Bối cảnh & Hiện tượng
- Khi nhận batch alert diện rộng (ví dụ Feed/Nuôi acc báo 16-30 máy fail) với chữ ký:
  `focus-device-issue:Device serial 'device:<serial>' was not found in adb devices.`
- Dấu hiệu đặc trưng:
  1. Có chuỗi `device:<serial>` do runner parse nhầm định dạng token dòng `adb devices` hoặc USB hub bị lag/drop bus tạm thời.
  2. Số lượng máy báo lỗi lớn (10-20 máy) nhưng thực tế phần lớn máy đã tự tái kết nối (auto-reconnect) sau đó vài phút.

## Quy trình Triage O(1) Bắt Buộc (Tuân thủ Farm Safety)
1. **Tuyệt đối không scan đĩa:**
   - Cấm dùng `grep -r`, `search_files` quét diện rộng hay duyệt đệ quy tìm log.
2. **Kiểm tra nhanh Canary theo Gate 0 & Invariant:**
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <M_CANARY>` để lấy danh sách thiết bị ADB online tức thì.
3. **Phân loại Online vs Offline qua `machine-map-80.txt`:**
   - Đọc mapping máy -> serial từ `C:/Users/Kibe/machine-map-80.txt` (hoặc `D:/Taadaa/machine-map-80.txt`).
   - Lọc danh sách máy trong alert đối chiếu với output `adb devices`.
   - Phân định rõ:
     - Số máy đã ONLINE trở lại bình thường (transient disconnect / hub hiccup).
     - Số máy thực sự OFFLINE vật lý (mất nguồn, đứt cáp, sleep sâu).
4. **Nghiệm thu Canary & Đính kèm MEDIA Gate (Gate 6):**
   - Chụp screencap O(1) máy canary đã online:
     `adb -s <serial> exec-out screencap -p > D:/Taadaa/m<N>_canary.png`
   - Báo cáo kết quả đính kèm `MEDIA:D:/Taadaa/m<N>_canary.png`.
   - Kết luận rõ ràng: cho phép fleet máy Online tiếp tục chạy, tách máy Offline cho can thiệp vật lý.
