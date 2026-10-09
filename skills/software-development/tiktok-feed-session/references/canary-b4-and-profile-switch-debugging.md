# Canary Test B4 & Profile Switch Debugging Guide

## 1. Lệnh thực thi Canary Test B4 (Targeted Recovery)
Để chạy canary test trên 1 máy cụ thể (ví dụ: Máy 79, Row 6, RecoveryTestSwipes 2):
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 79 -Row 6 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
*Ghi chú:*
- Bỏ cờ `-Run` để chạy ở chế độ **Preview/Dry-run**, kiểm tra toàn bộ arguments mà PowerShell sẽ truyền vào `python_runner\run_tiktok.py`.
- Sử dụng `-RecoveryTestSwipes 2` (sẽ random 2-3 swipes) cho targeted recovery.

## 2. Pre-flight Check: Stale Device Locks
- Trước khi chạy, kiểm tra khóa thiết bị tại:
  - `~/.codex/device-locks/machine_<m>.lock.json`
  - `~/.codex/device-locks/serial_<serial>.lock.json`
- Nếu file lock tồn tại:
  - Kiểm tra PID của tiến trình: nếu tiến trình đã chết (`owner_process_alive is False`), hoặc `owner_active == False` với tuổi lock > 600s, giải phóng file lock trước khi thực thi.

## 3. Khảo sát hiện trường lỗi: `profile username still mismatched after switch`
### Dấu hiệu nhận biết
- Lệnh dừng với exit code `2` và cảnh báo:
  `[ALERT] [MÁY N] Dừng: manual-needed | Lý do: profile username still mismatched after switch`
- Thư mục artifact: `.ai-runs/<timestamp>/machines/machine_<N>/<timestamp>/`

### Cách kiểm tra UI XML và nguyên nhân gốc
1. **Kiểm tra sheet switcher (`profile_preflight_switcher_1_guard/attempt_1/ui.xml`):**
   - Đọc danh sách các account trong switcher sheet (resource-id `com.ss.android.ugc.trill:id/l9b` / `mtx`).
   - Xác định xem target account từ workbook (Row N) có nằm trong danh sách hay không.
2. **Kiểm tra màn hình profile (`profile_identity/ui.xml`):**
   - Đọc username hiện tại qua `com.ss.android.ugc.trill:id/scn` (ví dụ `@refughbmh33`).
3. **Phân tích nguyên nhân:**
   - Nếu target account **có** trong switcher sheet nhưng sau 2 lần thử switch vẫn ở account cũ: flow `_resolve_profile_switch_anchor` hoặc click selector vào account con trong sheet bị trượt, hoặc TikTok không nhận touch event chuyển nick.
   - Nếu target account **không có** trong switcher sheet: flow cần điều hướng sang `auto_login_recovery` / đăng nhập tài khoản mới.

## 4. Kỷ luật tuyệt đối
- CẤM chạy lệnh `adb shell input tap/swipe` thủ công để chuyển account hay vượt qua bước kiểm tra.
- Mọi giải pháp xử lý phải được thực hiện thông qua cập nhật code runner (`python_runner/flows/feed_swipe_smoke.py`) hoặc điều chỉnh dữ liệu mapping/workbook chuẩn xác.
