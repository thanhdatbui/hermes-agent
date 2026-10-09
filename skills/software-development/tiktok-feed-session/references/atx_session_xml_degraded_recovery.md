# ATX Session XML Degraded Recovery & Pytest Isolation

## 1. Lỗi 'feed marker confirmed but XML unavailable: ATX_SESSION_UNAVAILABLE'

### Triệu chứng & Nguyên nhân
- Khi farm chạy ATX agent để capture UI dump, nếu stub ATX gặp glitch / timeout tạm thời sau retry và reset, `core/ui_capture.py` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")`.
- `FEED_CONFIRMED_XML_DEGRADED_ERRORS` tại `feed_swipe_smoke.py` (dòng ~302) trước đây chỉ chứa các mã lỗi UiAutomator cũ (`uiautomator_idle_state_error`, `ui_dump_failed`, v.v.), thiếu `"ATX_SESSION_UNAVAILABLE"` và `"atx_session_unavailable"`.
- Hậu quả: Khi ảnh chụp màn hình đã xác nhận feed thành công nhưng XML dump bị lỗi ATX, hệ thống không hạ cấp về `ExitStatus.DEGRADED` mà báo lỗi `status="failed"`, làm dừng phiên oan uổng.

### Quy tắc xử lý chuẩn trong `feed_swipe_smoke.py`
1. Luôn khai báo cả hai biến thể chữ hoa và chữ thường trong tập hợp:
   ```python
   FEED_CONFIRMED_XML_DEGRADED_ERRORS = {
       "uiautomator_idle_state_error",
       "uiautomator_null_root_node",
       "ui_dump_command_failed",
       "ui_dump_failed",
       "ui_dump_file_missing",
       "atx_session_unavailable",
       "ATX_SESSION_UNAVAILABLE",
   }
   ```
2. Tại tất cả các vị trí kiểm tra (`xml_error`, `home_navigation.status`, drift check), BẮT BUỘC kiểm tra case-insensitive hoặc đối chiếu cả `.lower()` / `.upper()`:
   ```python
   xml_err in FEED_CONFIRMED_XML_DEGRADED_ERRORS or xml_err.lower() in FEED_CONFIRMED_XML_DEGRADED_ERRORS
   ```

## 2. Pitfall Môi Trường Khi Chạy Pytest / Python Trong `tiktok-luot nuoi acc`

### Xung đột PYTHONPATH giữa Hermes Agent venv và farm automation env
- Môi trường terminal Windows có thể kế thừa `PYTHONPATH` trỏ vào `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`.
- Venv của Hermes dùng Python 3.11 trong khi `automation` env dùng Python 3.12, dẫn đến lỗi:
  `ImportError: cannot import name '_imaging' from 'PIL'`.
- Ngoài ra, việc thiếu `python_runner` và `automation-core/src` trong sys.path sẽ gây `ModuleNotFoundError: No module named 'core'`.

### Lệnh chạy Pytest chuẩn (Isolated PYTHONPATH)
Luôn prefix rõ ràng `PYTHONPATH` khi chạy test:
```bash
PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc/python_runner;D:/Taadaa/automation-core/src" \
D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest \
"D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_feed_session_smoke.py" -k "test_feed_confirmed_atx_session_unavailable"
```
