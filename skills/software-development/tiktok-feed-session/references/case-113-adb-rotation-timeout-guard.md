# Case 113: ADB Rotation Settings Timeout Guard & Single-Machine Canary Protocol

## 1. Hiện tượng & Bản chất lỗi
- **Hiện tượng:** Alert `[MÁY N]` báo dừng phiên nuôi acc/lướt feed với triệu chứng:
  `adb command timed out: ('...\\adb.exe', '-s', '<serial>', 'shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0')`
- **Nguyên nhân gốc:**
  - Trong `feed_swipe_smoke.py`, các bước trước và sau vòng lặp lướt video (`before_swipe_loop`, `after_swipe_loop`) gọi `ensure_portrait_rotation` (`device_prepare.py`).
  - Trong `automation-core/src/automation_core/startup.py`, hàm `lock_portrait_rotation` cũng thực thi lệnh tương tự.
  - Cả hai hàm này trước đây gọi `ctx.adb.shell(...)` với timeout mặc định 15s mà **KHÔNG bọc trong khối `try...except`**. Khi ADB transport bị lag hoặc socket bị nghẽn, `AdbClient` quăng `ADBError`, làm crash toàn bộ session thay vì chỉ ghi nhận step failed/degraded và tiếp tục phiên.

## 2. Giải pháp kỹ thuật chuẩn
1. **Cap Timeout ADB:**
   - Giới hạn timeout cho các lệnh `settings put/get` ở mức `<= 8.0s`:
     `timeout = min(ctx.timeout("adb_seconds", 15), 8.0)`
2. **Exception Guard độc lập:**
   - Bọc `try...except Exception as exc:` độc lập cho từng vòng lặp `settings put` và `settings get` của cả `accelerometer_rotation` và `user_rotation`.
   - Khi có lỗi / timeout: gán trạng thái `"failed"` vào dictionary quan sát (`observed`), bổ sung thông tin lỗi vào danh sách `errors`.
   - Trả về step row với `result="failed"` (hoặc degraded) nhưng **tuyệt đối không để exception văng ra ngoài** làm sập feed session.

## 3. Cú pháp Canary Test Máy Lẻ B4 chuẩn
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Row <Row> -Machines <N> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

### Cạm bẫy cần tránh khi chạy Canary:
1. **CẤM dùng `-LocalRun` khi truyền `-Machines <N>`:**
   - `run-feed-session.ps1` quy định `-LocalRun` bắt buộc đi kèm `-Preset full`. Nếu truyền cả `-LocalRun` và `-Machines` script sẽ quăng lỗi `LocalRun requires -Preset full so machines are discovered from the selected workbook row`.
   - Để chạy canary máy lẻ, chỉ cần truyền `-Machines <N> -Row <Row> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`.
2. **Cách xác định `-Row` (1..6):**
   - Đọc sheet `Accounts` trong `D:/Taadaa/tiktok-luot nuoi acc/data/taikhoan_run_safe.xlsx`.
   - Tìm dòng của Máy `N` tương ứng với nick trên alert để lấy chỉ số row (ví dụ Máy 21 có 6 nick từ row 1 đến 6; nick `lieumiyy3oa` nằm ở row 5).

## 4. Xử lý nghẽn I/O & Process treo trên Windows Host
- Khi các lệnh grep hoặc runner bị timeout bất thường, nguyên nhân thường do có các script chạy ngầm quét đĩa diện rộng (`glob.glob(recursive=True)`, `pytest` quét toàn bộ repo).
- Kiểm tra ngay bằng:
  ```bash
  wmic process where "name='python.exe'" get ProcessId,CommandLine
  ```
- Dùng `taskkill /F /PID <PID>` để giải phóng hàng đợi I/O trước khi chạy canary.
