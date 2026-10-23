# Preflight Drain Gate Cổng 5038 (Tiểu Vi) & Chống Báo Mất Kết Nối ADB Giả (23/10/2026)

## 1. Hiện Tượng Thực Tế (Bẫy Báo Mất Kết Nối 41 Máy)
- Trong ca nuôi feed TikTok, watchdog `feed_session_watchdog.py` báo cáo 41 máy trên Farm Kibe bị "Mất kết nối ADB/USB".
- Khi người dùng mở app Tiểu Vi (`放卫安卓投屏`), toàn bộ các máy đều đang sáng màn hình và truyền video bình thường.
- Chỉ có đúng 5 máy thực sự bị mất kết nối trên giao diện Tiểu Vi (M10, M14, M30, M35, M36).

## 2. Bản Chất Tranh Chấp WinUSB Cổng 5038 vs 5037
- Tiểu Vi sử dụng `adb.exe -P 5038` để duy trì kết nối stream 80 máy.
- Giao tiếp USB 2.0 EHCI bị nghẽn trần băng thông và driver WinUSB trên Windows khóa độc quyền endpoint, khiến daemon ADB chuẩn của hệ thống chạy cổng `5037` bị từ chối truy cập thiết bị (`device not found` hoặc `device offline`).
- Bộ phân loại lỗi trong watchdog gom `device not found` thành nhãn "Mất kết nối ADB/USB", tạo ra cảnh báo sai lệch nghiêm trọng.

## 3. Quy Trình Cứu Hộ Hiện Trường O(1) T0
Khi phát hiện nghi vấn mất kết nối diện rộng:
1. Kiểm tra liveness cổng 5038:
   ```python
   import socket
   s = socket.socket()
   is_open = (s.connect_ex(('127.0.0.1', 5038)) == 0)
   s.close()
   ```
2. Nếu cổng 5038 đang mở:
   - Cưỡng chế hạ GUI: `taskkill /F /IM xiaowei.exe`
   - Bắn lệnh kill ADB server 5038: `& "C:\Program Files (x86)\xiaowei\tools\adb.exe" -P 5038 kill-server`
   - Chờ 2 giây để Windows giải phóng bus USB và rebind thiết bị về cổng `5037`.
3. Kiểm tra lại ngay bằng `python D:/Taadaa/tools/inspect_machine.py <N>`. Máy sẽ nhận diện lại ngay lập tức mà không cần can thiệp phần cứng.

## 4. Cơ Chế Preflight Gate Tự Động (Đã Vá Vào Code)
Đã triển khai 2 tầng bảo vệ tự động:
1. **Tầng 1 — `run-feed-session.ps1`:**
   Trước khi phân bổ máy chạy feed, script tự động quét process `xiaowei` và TCP listening port `5038`. Nếu phát hiện sẽ tự động đóng và kill-server cổng 5038 trước khi spawn workers.
2. **Tầng 2 — `pre_session_device_gate.py`:**
   Hàm `filter_healthy_machines()` gọi `ensure_adb_port_5038_clean()` ngay ở đầu chu trình probe để đảm bảo toàn bộ quá trình kiểm tra sức khỏe thiết bị diễn ra trên cổng 5037 sạch.
