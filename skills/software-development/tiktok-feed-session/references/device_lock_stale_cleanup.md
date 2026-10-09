# Device Lock Stale Cleanup & Canary Recovery

## Hiện tượng
Khi một phiên feed session (hoặc alert) bị treo hoặc chết bất thường, process Python cũ có thể vẫn giữ lock hoặc để lại file stale lock:
`C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`

File lock này khiến các lượt chạy tiếp theo trên máy `<N>` bị từ chối hoặc kẹt hàng đợi (`queued_v2`).

## Quy trình kiểm tra & giải phóng Stale Lock

### 1. Kiểm tra tiến trình (Tránh lỗi MSYS Bash path mangling)
- **Pitfall**: Trong Git-Bash / MSYS trên Windows, gõ trực tiếp `tasklist //FI "PID eq <PID>"` hoặc `taskkill //F //PID <PID>` sẽ bị báo lỗi `ERROR: Invalid argument/option - '//FI'` hoặc `'//F'`.
- **Lệnh chuẩn kiểm tra**:
  ```powershell
  powershell.exe -Command "Get-Process -Id <PID> -ErrorAction SilentlyContinue | Format-List"
  # Hoặc kiểm tra chi tiết command line & thời gian tạo:
  powershell.exe -Command "Get-CimInstance Win32_Process -Filter 'ProcessId = <PID>' | Select-Object ProcessId, CommandLine, CreationDate"
  ```

### 2. Dọn dẹp tiến trình treo & xóa Stale Lock
- **Kết thúc tiến trình treo**:
  ```powershell
  cmd.exe /c "taskkill /F /PID <PID>"
  # Hoặc:
  powershell.exe -Command "Stop-Process -Id <PID> -Force"
  ```
- **Xóa file lock thiết bị**:
  ```bash
  rm -f "C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json"
  ```
- **Xác minh đã giải phóng**:
  ```powershell
  powershell.exe -Command "Test-Path 'C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json'"
  # Kết quả phải trả về False
  ```

### 3. Chạy Canary Test sau khi mở khóa
- Chạy canary test đơn máy để kiểm chứng luồng hoạt động ổn định:
  ```powershell
  env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
- Kiểm tra kết quả trong artifacts (`D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<timestamp>\summary.txt`) để đảm bảo `status: success` và `total_swipes_completed` đạt yêu cầu.
