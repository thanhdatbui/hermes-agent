# ADB Redacted Keyevent Timeout & Grep Trap (06/09/2026)

## 1. Hiện tượng & Giải mã lỗi `<redacted>` trong log ADB

### Hiện tượng
Khi runner gặp lỗi với thông điệp:
```text
ADBError: adb command timed out: ('C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe', '-s', 'ce0418244d10342502', 'shell', 'input', '<redacted>', '4')
```
Agent thường bối rối không biết `<redacted>` là gì và nghi ngờ do token/mật khẩu bị ẩn.

### Nguyên nhân gốc rễ (Root Cause)
1. Trong `automation-core/src/automation_core/adb.py`:
   ```python
   SENSITIVE_WORDS = ("TOKEN", "SECRET", "PASSWORD", "PASS", "COOKIE", "KEY")

   def _redact_arg(value: str) -> str:
       upper = value.upper()
       return "<redacted>" if any(word in upper for word in SENSITIVE_WORDS) else value
   ```
2. Do từ khóa `"KEY"` nằm trong danh sách nhạy cảm và được kiểm tra substring (`word in upper`), bất kỳ tham số nào chứa `"KEY"` (kể cả `"keyevent"`) đều bị ẩn thành `"<redacted>"`.
3. Lệnh thực tế được gọi chính là:
   ```bash
   adb -s <serial> shell input keyevent 4
   ```
   Trong đó `4` là `KEYCODE_BACK` (phím Back của Android). Tương tự, `keyevent 3` (phím Home) cũng sẽ bị redact thành `['shell', 'input', '<redacted>', '3']`.

## 2. Vì sao `input keyevent 4` bị timeout trên máy farm?

1. **Subsystem Input của Android bị nghẽn:** Trên các máy Samsung đời cũ (như Galaxy S7 / S7 Edge chạy Android 8), khi app TikTok đang load nặng, đổi Activity hoặc kẹt dialog hệ thống, lệnh `input` qua ADB có thể bị treo hoặc phản hồi quá 15s.
2. **Hành vi của `AdbClient`:**
   - Mặc định `default_timeout = 15s`.
   - Khi hết hạn, client thử `reconnect device` và retry 3 lần. Nếu vẫn quá hạn, client ném `ADBError: adb command timed out`.
3. **Các điểm gọi thiếu bảo vệ trong flow (`feed_swipe_smoke.py`):**
   - Trong `feed_swipe_smoke.py`, có nhiều vị trí gọi trực tiếp:
     ```python
     ctx.adb.shell(["input", "keyevent", "4"])
     ```
     mà không truyền `timeout` ngắn (ví dụ `timeout=3` hoặc `timeout=5`), và không có khối `try ... except (ADBError, subprocess.TimeoutExpired):` bọc quanh.
   - Khi lệnh Back phụ trợ bị treo 15s x 3 lần, nó đánh sập toàn bộ flow thay vì bỏ qua hoặc chuyển sang recovery khác.

## 3. Cách khắc phục chuẩn (Best Practices)

1. **Khi gọi `keyevent` phụ trợ trong flow:**
   Luôn truyền timeout ngắn và bọc try/except:
   ```python
   try:
       ctx.adb.shell(["input", "keyevent", "4"], timeout=ctx.timeout("adb_seconds", 5))
   except Exception as exc:
       logger.warning("Gặp lỗi khi gửi keyevent 4: %s", exc)
   ```
   - **Lưu ý quan trọng về logger trong `feed_swipe_smoke.py`:**
     `ctx.logger` là một instance của `JsonlLogger` (chỉ có method `.log()`, KHÔNG có `.warning()` hay `.error()`). Nếu gọi `ctx.logger.warning(...)` sẽ dính ngay `AttributeError: 'JsonlLogger' object has no attribute 'warning'`. Do đó, flow file BẮT BUỘC phải import `logging` và khởi tạo `logger = logging.getLogger(__name__)` ở module-level.
   - **5 vị trí gọi `keyevent 4` đã được chuẩn hóa trong `feed_swipe_smoke.py` (06/09/2026):**
     1. `_recover_post_swipe_to_for_you` (dòng ~5162): Thoát profile creator/người khác để định vị lại For You.
     2. `_recover_post_swipe_to_for_you` (dòng ~5185): Thoát subpage khi tap For You thất bại trước khi tap Home.
     3. `_capture_profile_switcher_xml_with_add_phone_guard` (dòng ~15750): Đóng overlay/keyboard khi account switcher chưa mở.
     4. `verify_and_switch_profile` (dòng ~17094): Đóng modal switcher khi expected account đã được chọn sẵn.
     5. `verify_and_switch_profile` (dòng ~17314): Đóng modal switcher khi không tìm thấy expected account trước recovery login.

2. **Cạm bẫy tham số Canary Launcher `run-feed-session.ps1`:**
   - Khi chạy canary test bỏ qua đồng bộ workbook tài khoản, tham số switch hợp lệ là `-SkipAccountWorkbookSync`.
   - Tuyệt đối KHÔNG gõ `-SkipAccountWorkbookUpdate` vì sẽ gây lỗi terminating:
     `NamedParameterNotFound,run-feed-session.ps1 (A parameter cannot be found that matches parameter name 'SkipAccountWorkbookUpdate')`.
   - **Cú pháp Canary chuẩn:**
     ```bash
     env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes (Get-Random -Minimum 2 -Maximum 5) -SkipAccountWorkbookSync -Run
     ```

3. **Cảnh giác bẫy `grep -rn` trên Windows:**
   - CẤM chạy `grep -rn` tìm kiếm qua nhiều thư mục mã nguồn lớn trên Windows. Subprocess git-bash có thể bị deadlock I/O hoặc chạm trần 900s timeout làm chết phiên làm việc.
   - Luôn dùng Python 1-liner đọc trực tiếp file đơn lẻ:
     ```python
     python -c "with open('path/to/file.py', 'r', encoding='utf-8') as f: ..."
     ```
