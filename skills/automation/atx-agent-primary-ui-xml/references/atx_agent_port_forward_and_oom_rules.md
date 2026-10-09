# Quy Tắc Điều Khiển UI XML & Dynamic Port Forwarding (atx-agent)

## 1. CẤM SHELL UIAUTOMATOR DUMP
- Trên Samsung S7 (Android 7), gọi shell `uiautomator dump` trên các màn hình phân cấp sâu (Settings, Dropdown, Menu) sẽ bị kernel Android OOM-kill ngay lập tức (`Killed, EXIT=137`), làm tiến trình subprocess bị ngậm timeout 10 phút (600s), treo cứng cả worker lẫn session.
- Toàn bộ script tools và worker BẮT BUỘC dùng `atx-agent` (port 7912):
  - Hierarchy XML: `http://127.0.0.1:{port}/dump/hierarchy`
  - Click: `http://127.0.0.1:{port}/jsonrpc/0` method: `click`

## 2. DETERMINISTIC PORT FORWARDING (CẤM HASH RANDOMIZATION)
- Khi mở dynamic port forward theo serial máy (ví dụ `17900 + offset`), CẤM TUYỆT ĐỐI dùng `hash(serial)`. Hàm `hash()` trong Python 3 có cơ chế *hash randomization* sinh ra giá trị khác nhau giữa các process/runtime, gây xung đột hoặc lệch port giữa các worker/process.
- BẮT BUỘC dùng `zlib.crc32`:
  ```python
  import zlib
  port = 17900 + (zlib.crc32(serial.encode("utf-8")) % 800)
  ```

## 3. TIMEOUT BOUNDED SUBPROCESS
- Mọi lệnh `subprocess.run` gọi `adb` BẮT BUỘC phải có `timeout=...` (khuyến nghị <= 15s) để chặn đứng nguy cơ socket stall làm subagent chạm trần 600s.
