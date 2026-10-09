# Focused Package Unavailable & ADB Host Reconnect (2026-09-05)

## 1. Hiện tượng hiện trường (Máy 46)
- **Triệu chứng**: Flow `feed-session-smoke` (repo `D:\Taadaa\tiktok-luot nuoi acc`) dừng phiên với `SAFETY_FAILED` kèm lý do `"focused package unavailable"` hoặc `"package unavailable"`.
- **Hiện trường**: TikTok vẫn đang mở và hiển thị Home Feed bình thường trên máy, nhưng script báo lỗi và dừng phiên thay vì tự động phục hồi và tiếp tục lướt feed.

## 2. Root Cause Analysis

### A. Bypass logic phục hồi focus trong `_is_launcher_focus_loss`
- **Vị trí**: `python_runner/flows/feed_swipe_smoke.py` (`_is_launcher_focus_loss`).
- **Cơ chế lỗi**: Khi ADB transport bị stall hoặc tạm thời không đọc được package qua XML/dumpsys, `get_focused_activity` trả về `{"package": None, "activity": None}`. Hàm `safety_check` trả về `SAFETY_FAILED, "focused package unavailable"`.
- `_is_launcher_focus_loss` trước đây chỉ kiểm tra `if focus_package:` và các keyword `"tiktok focus lost"` / `"focus lost"`. Khi `focus_package` là None hoặc chuỗi rỗng và reason là `"focused package unavailable"` hoặc `"package unavailable"`, hàm trả về `False`, khiến các logic phục hồi focus qua relaunch / reconnect bị bypass hoàn toàn và script dừng phiên `SAFETY_FAILED`.

### B. Xiaowei ADB `reconnect device` không reset host socket
- **Vị trí**: `D:\Taadaa\automation-core\src\automation_core\adb.py` (`_reconnect_device`).
- **Cơ chế lỗi**: Trên Xiaowei ADB, lệnh `adb -s <serial> reconnect device` trả về exit code `0` nhưng không giải phóng transport socket phía host. Nhánh `if res.returncode != 0:` bỏ qua lệnh `adb -s <serial> reconnect` (host-side reconnect), khiến ADB transport tiếp tục bị stall.

## 3. Quy chuẩn Khắc phục (Resolution Pattern)

1. **`python_runner/flows/feed_swipe_smoke.py`**:
   Bắt buộc nhận diện `"package unavailable"` và `"focused package unavailable"` là recoverable focus loss trong `_is_launcher_focus_loss`:
   ```python
   if "package unavailable" in reason_lower or "focused package unavailable" in reason_lower:
       return True
   if focus_package:
       return True
   return "tiktok focus lost" in reason_lower or "focus lost" in reason_lower
   ```

2. **`automation_core/adb.py`**:
   Trong `_reconnect_device()`, luôn thực hiện thêm lệnh `[self.adb_path, "-s", self.serial, "reconnect"]` (host-side reconnect) bất kể exit code của `reconnect device` để giải phóng socket trên Xiaowei ADB.
   Đồng bộ sang: `D:/Taadaa/python-envs/automation/Lib/site-packages/automation_core/adb.py`.

3. **`python_runner/flows/observe.py`**:
   Trong `get_focused_activity()`, nếu vòng lặp candidates dumpsys thất bại ở attempt đầu, gọi `ctx.adb.reconnect()` trước attempt tiếp theo để gỡ stall transport socket thay vì trả thẳng `{"package": None, "activity": None}`.

4. **Canary Verification**:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 46 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
   Nghiệm thu: `swipes_completed = 2`, `final_status = success`.
