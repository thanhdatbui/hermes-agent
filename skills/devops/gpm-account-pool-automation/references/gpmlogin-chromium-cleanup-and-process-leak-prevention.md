# GPMLogin Chromium Process Leak Prevention & Cleanup Protocol

## 1. Nguyên nhân rò rỉ tiến trình Chrome trong GPMLogin
- Khi đóng profile qua API `/profiles/stop/{profile_id}`, một số phiên bản GPMLogin Local API không tự terminate triệt để tiến trình con (`chrome.exe`), khiến Chromium vẫn chạy ngầm chiếm RAM, khóa file profile `Preferences`/`SingletonLock`, gây xung đột ở lần khởi động sau.
- Một số phiên bản GPM API yêu cầu endpoint `/profiles/close/{profile_id}` thay vì hoặc kết hợp với `/profiles/stop/{profile_id}`.

## 2. Kỷ luật Bất biến khi Dọn dẹp (Bảo vệ Chrome Cá nhân)
- **TUYỆT ĐỐI KHÔNG** dùng `taskkill /F /IM chrome.exe` bừa bãi vì sẽ làm crash toàn bộ trình duyệt làm việc cá nhân của người dùng.
- **TUYỆT ĐỐI BẢO VỆ** port `9222` (cổng remote-debugging mặc định của trình duyệt chính).
- Chỉ dọn dẹp các tiến trình thỏa mãn đồng thời:
  1. Tiến trình mang tên `chrome.exe`.
  2. Command line chứa định danh `gpmlogin` (trong đường dẫn binary hoặc `--user-data-dir`).
  3. Khớp một trong các tiêu chí:
     - Flag `--remote-debugging-port={remote_port}` (với port hợp lệ != 9222).
     - Flag `--user-data-dir` trỏ tới đường dẫn `profile_path` của profile.
     - Profile ID xuất hiện trong command line.

## 3. Triển khai chuẩn trong Python (`psutil`)

```python
import os
import re
import time
import requests
import psutil
import logging

logger = logging.getLogger("gpm_cleanup")

def stop_and_cleanup_gpm_profile(base_url: str, profile_id: str, remote_port: int = None, profile_path: str = None, timeout: int = 15):
    # 1. Gọi fallback cả 2 API close và stop
    for endpoint in ["close", "stop"]:
        try:
            res = requests.get(f"{base_url}/profiles/{endpoint}/{profile_id}", timeout=timeout)
            if res.status_code == 200:
                break
        except Exception as e:
            logger.debug(f"API {endpoint} error: {e}")

    # 2. Chờ 1.0s cho trình duyệt lưu cache / graceful shutdown
    time.sleep(1.0)

    # 3. Quét psutil dọn dẹp tiến trình kẹt
    target_port_flag = rf"^--remote-debugging-port={remote_port}$" if (remote_port and 0 < remote_port <= 65535 and remote_port != 9222) else None
    norm_target_path = os.path.normpath(profile_path).lower() if profile_path else None
    clean_pid = profile_id.lower()

    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            p_name = (p.info.get('name') or '').lower()
            if 'chrome' in p_name:
                cmdline = p.info.get('cmdline') or []
                # Chỉ xử lý nếu thuộc GPMLogin
                if not any('gpmlogin' in arg.lower() for arg in cmdline):
                    continue

                matched = False
                if target_port_flag and any(re.match(target_port_flag, arg) for arg in cmdline):
                    matched = True
                if not matched and norm_target_path:
                    for arg in cmdline:
                        if arg.startswith("--user-data-dir="):
                            val = arg.split("=", 1)[1].strip('"\'')
                            norm_val = os.path.normpath(val).lower()
                            if norm_val == norm_target_path or norm_target_path in norm_val:
                                matched = True
                                break
                if not matched:
                    for arg in cmdline:
                        if clean_pid in arg.lower():
                            matched = True
                            break

                if matched:
                    p.terminate()
                    try:
                        p.wait(timeout=1.5)
                    except Exception:
                        p.kill()
        except Exception:
            continue
```

## 4. Kỷ luật trong khối `finally` của Script chạy batch
Mọi automation script dùng GPM + Playwright CDP **bắt buộc** có khối `finally`:
```python
finally:
    if context:
        try: context.close()
        except Exception: pass
    if browser:
        try: browser.close()
        except Exception: pass
    if pw:
        try: pw.stop()
        except Exception: pass
    stop_and_cleanup_gpm_profile(GPM_API_BASE, profile_id, remote_port=port, profile_path=prof_dir)
```
