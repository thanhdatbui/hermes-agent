# Focused Package Unavailable Recovery (2026-09-05)

## 1. Hiện tượng & Triệu chứng (Máy 46 & cụm farm)
- **Triệu chứng**: Flow `feed-session-smoke` (repo `D:\Taadaa\tiktok-luot nuoi acc`) dừng phiên với `SAFETY_FAILED` kèm lý do:
  `focused package unavailable` hoặc `package unavailable`.
- **Hiện trường**: Thiết bị vẫn đang mở TikTok Home Feed bình thường, nhưng script báo lỗi và dừng toàn bộ flow thay vì tự động phục hồi và tiếp tục lướt feed.

## 2. Root Cause Analysis

### A. `_is_launcher_focus_loss` bypass focus recovery khi focus_package rỗng
- **Vị trí**: `python_runner/flows/feed_swipe_smoke.py` (`_is_launcher_focus_loss`).
- **Cơ chế lỗi**:
  Khi ADB transport bị stall hoặc tạm thời không lấy được package qua XML/dumpsys, `get_focused_activity` trả về `{"package": None, "activity": None}`. Hàm `safety_check` trả về `SAFETY_FAILED, "focused package unavailable"`.
  Hàm `_is_launcher_focus_loss` trước đây chỉ kiểm tra:
  ```python
  if focus_package:
      return True
  return "tiktok focus lost" in reason_lower or "focus lost" in reason_lower
  ```
  Vì `focus_package` là `""` và `reason_lower` chứa `"focused package unavailable"`, điều kiện trả về `False`. Kết quả: script coi đây không phải mất focus và không kích hoạt nhánh relaunch / reconnect / recapture mà dừng thẳng phiên.

### B. Xiaowei ADB `reconnect device` không reset host socket
- **Vị trí**: `automation-core/src/automation_core/adb.py` (`_reconnect_device`).
- **Cơ chế lỗi**:
  Xiaowei ADB trả returncode = 0 cho lệnh `adb -s <serial> reconnect device`, khiến khối `if res.returncode != 0:` không được kích hoạt để gọi host-side `adb -s <serial> reconnect`. Do đó socket phía host Windows vẫn bị treo.

### C. Thiếu Host Reconnect trong `get_focused_activity`
- **Vị trí**: `python_runner/flows/observe.py` (`get_focused_activity`).
- Khi XML capture và dumpsys thất bại do socket transport bị nghẽn, việc gọi `ctx.adb.reconnect()` giữa các attempts cho phép host khôi phục kết nối ngay trong cùng lần gọi.

## 3. Quy chuẩn Sửa chữa & Khắc phục (Resolution Pattern)

1. **Cập nhật `_is_launcher_focus_loss`**:
   Bắt buộc nhận diện `"package unavailable"` và `"focused package unavailable"` là recoverable focus loss:
   ```python
   if "package unavailable" in reason_lower or "focused package unavailable" in reason_lower:
       return True
   if focus_package:
       return True
   return "tiktok focus lost" in reason_lower or "focus lost" in reason_lower
   ```

2. **Cập nhật `_reconnect_device` trong `automation_core/adb.py`**:
   Luôn thực hiện host reconnect:
   ```python
   subprocess.run([self.adb_path, "-s", self.serial, "reconnect", "device"], ...)
   subprocess.run([self.adb_path, "-s", self.serial, "reconnect"], ...)
   ```
   Đồng bộ sang `D:/Taadaa/python-envs/automation/Lib/site-packages/automation_core/adb.py`.

3. **Cập nhật `_relaunch_and_poll_tiktok_focus`**:
   Gọi `ctx.adb.reconnect()` ở đầu hàm để đảm bảo kênh truyền thông suốt trước khi wake/unlock và relaunch app.

4. **Canary Test an toàn**:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
   Nghiệm thu: `swipes_completed = 2`, `final_status = success`.
