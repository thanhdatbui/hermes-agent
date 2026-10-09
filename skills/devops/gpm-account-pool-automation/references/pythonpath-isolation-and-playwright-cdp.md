# Pitfalls & Environment Isolation in GPMLogin + Playwright

## 1. Ô nhiễm biến môi trường PYTHONPATH giữa các virtual environments
### Triệu chứng
Khi thực thi script Playwright qua Python venv chuyên biệt (ví dụ `/d/Taadaa/python-envs/automation/Scripts/python.exe`), tiến trình ném ngoại lệ:
```text
ModuleNotFoundError: No module named 'greenlet._greenlet'
```
hoặc lỗi import module Playwright C-extensions.

### Nguyên nhân
Tiến trình con (subprocess) từ môi trường Hermes Agent tự động thừa hưởng biến môi trường `PYTHONPATH` trỏ tới:
`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`.
Dẫn đến việc Python nạp nhầm package `greenlet` / `playwright` của virtualenv Hermes (khác phiên bản Python hoặc thiếu build binary) thay vì nạp từ virtualenv chuyên biệt.

### Cách khắc phục chuẩn
1. **Từ Terminal / Shell:** Luôn làm sạch `PYTHONPATH` trước khi gọi python:
   ```bash
   PYTHONPATH="" /d/Taadaa/python-envs/automation/Scripts/python.exe script.py
   ```
2. **Trong mã nguồn Python (ngay dòng đầu):**
   ```python
   import os, sys
   os.environ.pop("PYTHONPATH", None)
   sys.path = [p for p in sys.path if "hermes-agent" not in p]
   ```

## 2. Kết nối Playwright CDP vào GPMLogin
- Luôn đặt timeout cho `browser = playwright.chromium.connect_over_cdp(f"http://{remote_addr}", timeout=10000)`.
- Khi dừng hoặc gặp lỗi ngoại lệ, bắt buộc bọc trong khối `finally:` để gọi `requests.get(f"http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}")`, tránh profile chạy ngầm chiếm dụng tài nguyên và proxy port.
