# ADB Keyevent Redaction, Safe Keyevent Wrappers & Stale Lock Canary Recovery

## 1. Giải Mã Cụm `<redacted>` Trong Log ADB Timeout
Khi hệ thống bắn Farm Alert có dạng:
```text
adb command timed out: ('...adb.exe', '-s', '<serial>', 'shell', 'input', '<redacted>', '4')
```
- **Nguyên nhân:** Trong `D:/Taadaa/automation-core/src/automation_core/adb.py`, danh sách `SENSITIVE_WORDS = ("TOKEN", "SECRET", "PASSWORD", "PASS", "COOKIE", "KEY")`.
- **Cơ chế:** Từ khóa `KEY` trùng với chuỗi con trong `keyevent`. Do đó, lệnh Android chuẩn `['shell', 'input', 'keyevent', '4']` (nút Back) hoặc `keyevent 3` (nút Home) tự động bị redact thành `['shell', 'input', '<redacted>', '4']`.
- **Chẩn đoán:** Khi thấy `<redacted>` đi liền sau `input` và trước số keycode (`4` = Back, `3` = Home, `66` = Enter), đó chắc chắn là `keyevent`.

---

## 2. Kỹ Thuật Bọc An Toàn Cho Các Lệnh `keyevent` Trong Feed Session
Trong `feed_swipe_smoke.py`, các vị trí gửi phím Back phụ trợ không được để unhandled exception:
- **Vấn đề:** Thiết bị Samsung khi đổi màn hình hoặc tải profile switcher có thể phản hồi chậm khiến transport ADB quá hạn 15s. Nếu gọi `ctx.adb.shell(["input", "keyevent", "4"])` không bọc try/catch, `ADBError` sẽ làm sập toàn bộ flow phiên nuôi.
- **Giải pháp:** Bọc toàn bộ các lệnh Back phụ trợ bằng khối `try/except Exception` kèm timeout ngắn (3-5s) và log warning:
```python
try:
    ctx.adb.shell(["input", "keyevent", "4"], timeout=ctx.timeout("adb_seconds", 5))
except Exception as exc:
    logger.warning("Gặp lỗi khi gửi keyevent 4: %s", exc)
```
- **Các vị trí trọng yếu trong `feed_swipe_smoke.py`:**
  1. `_recover_post_swipe_to_for_you`: Thoát trang cá nhân creator/người khác trước khi tap For You.
  2. `_capture_profile_switcher_xml_with_add_phone_guard`: Đóng bàn phím hoặc overlay khi account switcher chưa mở.
  3. `verify_and_switch_profile` (`dismiss_already_selected_switcher` & `dismiss_switcher_on_missing_account`): Đóng switcher modal.

---

## 3. Cạm Bẫy Stale Device Lock Khi Chạy Canary
- **Triệu chứng:** Khi chạy canary sau khi patch code, script trả về:
  ```text
  multi-machine-feed-session has locked machine(s) requiring operator decision
  Status: manual-needed / skipped-device-locked (Exit code 2)
  ```
- **Nguyên nhân:** Phiên bị lỗi trước đó dừng đột ngột nhưng vẫn giữ file lock tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` trỏ tới PID cũ (`python.exe`).
- **Quy trình giải phóng an toàn:**
  1. Kiểm tra PID từ file lock: `tasklist /FI "PID eq <PID>"`.
  2. Nếu tiến trình đã chết hoặc bị treo: Buộc dừng tiến trình `taskkill /F /PID <PID>`.
  3. Xóa file lock: `Remove-Item "C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json"`.
  4. Chạy lại Canary test live.

---

## 4. Chuẩn Cú Pháp Canary Test Với `run-feed-session.ps1`
1. **Bỏ qua cập nhật Workbook:** Dùng `-SkipAccountWorkbookSync` (tránh dùng `-SkipAccountWorkbookUpdate` vì không tồn tại trong script).
2. **Kích hoạt Live Execution:** Script mặc định chỉ chạy ở chế độ Preview (Dry-run). **BẮT BUỘC** truyền thêm cờ `-Run` để thực thi thật trên thiết bị:
```powershell
env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
