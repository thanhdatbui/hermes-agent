# Canary Test & Device Lock Handling Guide (TikTok Feed Session)

## 1. Lệnh Chạy Canary Test Chuẩn
Khi cần chạy canary test trên 1 máy (ví dụ Máy 36) để kiểm tra swipe / recovery:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 36 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
- `-RecoveryTestSwipes 2`: Runner sẽ random trong khoảng 2-3 swipe để kiểm tra recovery tối thiểu.
- `-SkipAccountWorkbookSync`: Bỏ qua sync workbook nếu chỉ chạy test đơn máy.

## 2. Xử Lý Khi Gặp Lỗi `skipped-device-locked` / `has locked machine(s)`
- **Hiện tượng:** Runner dừng ngay với `Status: manual-needed` và log ghi `multi-machine-feed-session has locked machine(s) requiring operator decision`.
- **Nguyên nhân:** File lock tồn tại tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` do tiến trình Cron lớn (ví dụ `hermes-cron-kibe`) đang chạy feed đa máy trên máy đó.
- **Quy tắc an toàn:**
  1. **TUYỆT ĐỐI KHÔNG** dùng `taskkill` diệt tiến trình cha hay tự tiện xoá file `.lock.json`.
  2. Kiểm tra PID từ file lock hoặc log summary:
     ```powershell
     powershell.exe -Command "Get-Process -Id <PID> -ErrorAction SilentlyContinue"
     ```
  3. Kiểm tra artifact của máy trong batch cron hiện tại (ví dụ `D:\Taadaa\runtime\kibe\live\<date>\<batch>\machines\machine_<N>`).
  4. Nếu máy đang hoàn tất slot nuôi acc, đợi slot kết thúc (khoảng vài chục giây đến vài phút). Khi máy xong, runner cron sẽ tự động giải phóng `machine_<N>.lock.json`.
  5. Sau khi file lock tự xoá, khởi chạy lại lệnh canary test.

## 3. Chụp Ảnh Screencap Bằng Chứng Sau Canary
- Trên môi trường Windows host, lệnh `adb` có thể không nằm trong biến môi trường `$PATH` mặc định của MSYS / Git Bash.
- **Đường dẫn ADB chuẩn:**
  - CMD / PowerShell: `C:\Program Files (x86)\xiaowei\tools\adb.exe`
  - Git Bash / MSYS: `"/c/Program Files (x86)/xiaowei/tools/adb.exe"`
- **Lệnh chụp ảnh màn hình lưu bằng chứng:**
  ```bash
  "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <device_serial> exec-out screencap -p > "D:/Taadaa/runtime/kibe/live/canary_m<N>_done.png"
  ```
  *(Ví dụ Máy 36 có serial `ce10160ac8f1962305`)*
