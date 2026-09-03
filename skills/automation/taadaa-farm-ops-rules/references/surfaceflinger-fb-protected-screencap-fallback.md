# SurfaceFlinger FB is Protected Screencap Fallback Pattern

## Bối cảnh & Hiện tượng
Khi chạy farm Android (đặc biệt các máy Samsung S7 / Android 8.0) kèm theo phần mềm điều khiển/mirror màn hình (scrcpy, Xiaowei, TotalControl) hoặc khi ứng dụng có cờ `FLAG_SECURE` / bề mặt bảo vệ:
- Lệnh `adb exec-out screencap -p` hoặc `adb shell screencap` bị SurfaceFlinger từ chối với lỗi logcat:
  `W/SurfaceFlinger: FB is protected: PERMISSION_DENIED`
- Kết quả đầu ra trả về chỉ có 12 byte rỗng (`b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'`), kích thước quá nhỏ (< 1000 bytes).
- Nếu mã nguồn gửi cảnh báo Telegram (`send_farm_machine_alert`) chỉ dựa vào `screencap`, nó sẽ bị mất ảnh và chuyển thành tin nhắn text thuần không có Banner Đỏ.

## Cơ chế xử lý đa tầng (Multi-layer Fallback)

### Tầng 1: `adb exec-out screencap -p` (Primary)
- Nhanh nhất khi thiết bị ở trạng thái bình thường.
- Kiểm tra `len(stdout) > 1000`. Nếu thất bại, chuyển sang Tầng 2.

### Tầng 2: ATX-Agent / UiAutomator2 JSON-RPC `takeScreenshot` (Port 7912 / 9008)
- Bỏ qua cơ chế bảo vệ SurfaceFlinger framebuffer bằng cách đọc trực tiếp từ bộ đệm đồ họa của UiAutomator2 server (`com.github.uiautomator.stub.Stub`).
- Các bước thực hiện:
  1. Bind một ephemeral local port còn trống.
  2. Tạo port forward: `adb -s <serial> forward tcp:<local_port> tcp:7912` (hoặc `tcp:9008`).
  3. Gửi HTTP POST tới `http://127.0.0.1:<local_port>/jsonrpc/0` với payload:
     ```json
     {
       "jsonrpc": "2.0",
       "method": "takeScreenshot",
       "params": [1.0, 90],
       "id": 1
     }
     ```
  4. Nhận chuỗi Base64 từ trường `result` và `base64.b64decode` ra dữ liệu ảnh PNG/JPEG gốc (kích thước 1080x1920).
  5. Xóa port forward trong khối `finally:`.

### Tầng 3: Shell screencap ghi file tạm `/sdcard/__alert_screencap.png` & `cat`
- Phương án dự phòng cuối cùng nếu UiAutomator2 server chưa khởi động.
