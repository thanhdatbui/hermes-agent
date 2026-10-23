# Preflight XiaoWei Port 5038 & ADB Bus Protection Pattern

## Bối Cảnh & Hiện Tượng Thực Tế
- Khi ứng dụng Tiểu Vi (`xiaowei.exe`) được mở để quan sát màn hình farm, tiến trình con `adb.exe -P 5038` chiếm giữ các endpoints USB và chia rẽ WinUSB bus.
- Cổng mặc định `5037` của hệ thống nuôi acc bị mất kết nối thiết bị hàng loạt (`device not found`).
- Watchdog feed session phân loại nhầm toàn bộ thành lỗi "Mất kết nối ADB/USB (40+ máy)" gây hoang mang, trong khi thực tế thiết bị vẫn sáng màn hình và truyền frame bình thường trên Tiểu Vi.

## Quy Tắc Bắt Buộc Trong Preflight Gate
1. **Kiểm tra trước khi khởi chạy feed session:**
   - Trong `run-feed-session.ps1` hoặc launcher nuôi acc, bắt buộc thăm dò cổng 5038 trước khi phân bổ thiết bị.
   - Nếu phát hiện cổng 5038 đang LISTEN:
     * Ưu tiên gọi `adb.exe -P 5038 kill-server` qua binary XiaoWei (`C:\Program Files (x86)\xiaowei\tools\adb.exe`).
     * Đợi 1 giây để socket stack nhả trạng thái.
     * Kiểm tra lại cổng 5038. Nếu vẫn còn listener chiếm dụng: BẮT BUỘC ném lỗi fail-closed `PREFLIGHT_PORT_5038_BLOCKED`, tuyệt đối không spawn luồng nuôi cắm vào USB bus đang nghẽn.
2. **Khắc phục bẫy mảng $null trong PowerShell:**
   - Trong PowerShell, `@($null).Count` bằng **1**.
   - Do đó, khi kiểm tra kết nối bằng `Get-NetTCPConnection`:
     `@(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_ })`
   - Bắt buộc phải có `| Where-Object { $_ }` để lọc bỏ phần tử `$null` khi không có connection nào, tránh false-positive nhận nhầm cổng đang bận.
3. **Telemetry có cấu trúc:**
   - Phát sinh log telemetry dạng JSON một dòng khi phát hiện cổng bận:
     `[PREFLIGHT_DIAGNOSTIC] {"event": "preflight_port_5038", "initial_pid": <PID>, "kill_attempted": true/false, "released": true/false}`
   - Không nuốt lỗi im lặng hoặc để xảy ra false-negative làm trôi ca nuôi.
