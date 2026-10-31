# Khắc Phục Lỗi ATX-Agent HTTP 502 / UiAutomator Treo Trên Thiết Bị Samsung S7

## 1. Hiện Tượng & Nguyên Nhân Gốc (Root Cause)
- **Hiện tượng**:
  - Gọi ATX-Agent RPC qua port 7912 (`/jsonrpc/0`, ví dụ `dumpWindowHierarchy`, `click`) bị văng lỗi:
    `urllib.error.HTTPError: HTTP Error 502: Bad Gateway`
  - ADB port forwarding hoạt động nhưng tiến trình xử lý JSON-RPC phía sau bị từ chối kết nối.
- **Nguyên nhân kỹ thuật**:
  - `atx-agent` (chạy native binary Go trên Android) hoạt động như một reverse proxy chuyển tiếp các lệnh RPC sang tiến trình `app-process` chạy gói kiểm thử AndroidJUnitRunner của `com.github.uiautomator`.
  - Khi thiết bị Android bị đầy bộ nhớ, bị lag hoặc tiến trình `uiautomator` cũ bị crash / deadlock không kịp giải phóng socket, `atx-agent` không thể kết nối tới backend localhost của uiautomator stub -> ném HTTP 502 Bad Gateway ra ngoài.

## 2. Quy Trình Khôi Phục Nhanh O(1) Bằng Lệnh ADB Trực Tiếp

### B1: Kiểm tra trạng thái tiến trình trên máy
```bash
python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell "ps | grep -E 'atx|uiautomator'"
```
- Nếu chỉ thấy `atx-agent` mà không thấy `com.github.uiautomator` -> tiến trình uiautomator stub đã chết.
- Nếu thấy cả hai nhưng RPC vẫn 502 -> uiautomator stub bị deadlock / zombie socket.

### B2: Dọn dẹp & Khởi động lại service
1. **Kill tiến trình cũ**:
   ```bash
   python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell "pkill -f uiautomator; pkill -f atx-agent"
   ```
2. **Khởi động lại atx-agent daemon**:
   ```bash
   python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell "/data/local/tmp/atx-agent server -d"
   ```
3. **Kích hoạt lại uiautomator instrumentation stub**:
   ```bash
   python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell "nohup am instrument -w -r -e debug false -e class com.github.uiautomator.stub.Stub com.github.uiautomator.test/android.support.test.runner.AndroidJUnitRunner > /dev/null 2>&1 &"
   ```

## 3. Fallback Cấp Tốc Bằng ADB Thuần Khi Không Muốn Khởi Động Lại Service
Nếu đang trong ca trực gấp mà uiautomator stub bị treo và không muốn can thiệp daemon:
- **Đọc cấu trúc UI (Dump XML)**:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell uiautomator dump /data/local/tmp/uidump.xml
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell cat /data/local/tmp/uidump.xml
  ```
  *(Lệnh `uiautomator dump` hệ thống của Android luôn chạy độc lập với atx-agent, trả về XML cây giao diện 100% chuẩn xác)*.
- **Chụp màn hình nghiệm thu (Gate 6)**:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> exec-out screencap -p > <output_path.png>
  ```
