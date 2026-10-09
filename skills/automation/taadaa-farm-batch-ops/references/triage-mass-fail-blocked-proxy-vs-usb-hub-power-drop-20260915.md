# Triage Mass-Fail: Phân biệt Nhãn "blocked-proxy-vpn" với Sự Cố Sập Nguồn / Rớt USB Hub Vật Lý (2026-09-15)

## 1. Hiện Tượng & Cạm Bẫy Nhãn Lỗi (False "Proxy/VPN" Label)
- Khi chạy batch nuôi acc (Feed Session) hoặc upload, watchdog báo cáo hàng loạt máy thất bại (ví dụ 72/80 máy fail) với event count:
  `blocked-proxy-vpn: 71`
- **Cạm bẫy:** Người vận hành hoặc AI dễ bị đánh lừa bởi tên nhãn `blocked-proxy-vpn`, vội vàng đi kiểm tra Proxy Mobi, Proxy MikroTik hay VPN interface.
- **Bản chất logic trong runner (`device_prepare.py` / preflight):** Khi preflight kiểm tra thiết bị, nếu lệnh `adb -s <serial> ...` thất bại do thiết bị offline hoặc không tìm thấy (`device '...' not found`), preflight ném ngoại lệ hoặc fallback chặn device-lock và gán status chung là `blocked-proxy-vpn`.

## 2. Quy Trình Điều Tra O(1) Phân Tầng (Zero Quét Đĩa)

### Bước 1: Đọc Nguyên Nhân Gốc Trong Log Máy Đại Diện (O(1))
- Mở trực tiếp `summary.txt` của 1 máy trong thư mục run gần nhất:
  `D:/Taadaa/runtime/kibe/live/<DATE>/<ROW_DIR>/<TIMESTAMP>/machines/machine_<N>/<TIMESTAMP>/summary.txt`
- Kiểm tra trường `stop_reason`:
  ```text
  stop_reason: device is offline or ADB/USB disconnected for <serial>: device offline or ADB/USB disconnected: adb.exe: device '<serial>' not found
  ```
- Nếu xuất hiện `device '<serial>' not found` $\rightarrow$ Đây là lỗi mất kết nối ADB / USB, KHÔNG PHẢI lỗi proxy mạng.

### Bước 2: Kiểm Tra Tầng ADB Server
- Chạy lệnh:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py <N>
  # hoặc: "/c/Program Files (x86)/xiaowei/tools/adb.exe" devices
  ```
- Quan sát số lượng thiết bị online: Nếu từ 74-80 máy chỉ còn lại 8 máy (ví dụ chỉ còn cụm máy 73–80), sự cố mang tính cụm box phần cứng.

### Bước 3: Chẩn Đoán Tầng Phần Cứng USB Windows Qua PowerShell
- Quét nhanh trạng thái PnP của các thiết bị Samsung & USB Hubs:
  ```powershell
  # 1. Đếm tổng thiết bị Samsung theo trạng thái:
  Get-PnpDevice | Where-Object { $_.FriendlyName -match 'SAMSUNG|Android|Galaxy' } | Group-Object Status | Select-Object Name, Count

  # 2. Kiểm tra trạng thái các cụm USB Hub (chip CH334/CH340 VID_1A86 trong Box Phone):
  Get-PnpDevice -Class 'USB' | Where-Object { $_.FriendlyName -match 'Hub' } | Select-Object Status, FriendlyName, InstanceId
  ```
- **Dấu hiệu đặc trưng:**
  - `Unknown: 300+` và `OK: ~32` (tương ứng 8 máy còn lại x 4 interface).
  - Hàng loạt `Generic USB Hub (USB\VID_1A86&PID_8095)` chuyển sang trạng thái `Unknown` $\rightarrow$ Toàn bộ Box S7 bị ngắt kết nối vật lý với bo mạch chủ PC.

## 3. Bản Chất S7 ROM Gốc & Biện Pháp Xử Lý Vật Lý
- Box S7 chạy ROM gốc khi sụt áp / cúp điện sẽ tắt ngấm hoặc rơi vào chế độ sạc pin (LPM - Low Power Mode), KHÔNG tự khởi động lại khi có điện trở lại.
- **Biện pháp khắc phục:**
  1. Kiểm tra nguồn điện cấp cho các Box và bộ chia nguồn PC.
  2. Cắm lại cáp USB Host kết nối từ Box vào thùng máy PC.
  3. Bật nguồn thủ công từng máy S7.
  4. Sau khi `adb devices` nhận lại đủ máy, các cronjob kế tiếp sẽ tự động chạy bình thường mà không cần sửa code.
