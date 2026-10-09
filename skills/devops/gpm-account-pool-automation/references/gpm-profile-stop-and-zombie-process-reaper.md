# GPMLogin Profile Stop & Zombie Process Reaper Pattern

## 1. Bối cảnh & Hiện tượng lỗi (Incident Analysis)
Khi chạy batch tự động mở nhiều profile GPM (ví dụ batch ChatGPT, Checkmail, Google OAuth):
- **Bẫy chí mạng của GPM Local API v3 (`profiles/stop/{pid}`):**
  Endpoint `GET /api/v3/profiles/stop/{profile_id}` trả về `{"success": True}` trên giao diện, **nhưng HOÀN TOÀN KHÔNG DIỆT TIẾN TRÌNH `chrome.exe` THỰC TẾ TRÊN WINDOWS!**
  Mỗi profile Chromium khi mở sẽ sinh ra 1 tiến trình mẹ và 6-8 tiến trình con (GPU Process, Network Service, Audio Service, Renderers).
  Khi chạy batch qua 40-50 profile, nếu chỉ gọi API `profiles/stop`, toàn bộ các cây tiến trình này tiếp tục chạy ngầm trong Task Manager.
  Hậu quả: Hơn 400 tiến trình Chrome rác ngốn sạch 100% RAM và CPU, gây treo cứng (freeze/lag) toàn bộ máy tính của người dùng!
- Khi trình duyệt bị kẹt bởi modal cảnh báo của Chromium ("Restore pages"), GPMLogin API càng bất lực.
- **Phân biệt tiến trình trên Taskbar:**
  Các icon hình vuông tối màu đánh số (ví dụ `130`, `131`, ... `160`) trên Taskbar có thể là các cửa sổ mirror của `xiaowei.exe` (Group Control quản lý dàn Samsung Galaxy S7 Phone Farm), tuyệt đối không nhầm lẫn với profile GPM và không được tắt nhầm `xiaowei.exe`.

---

## 2. Chuẩn mực Process Reaper 2 Tầng: PID Tree Force-Kill (Reviewer & Farm-Approved)

BẮT BUỘC áp dụng cơ chế 2 tầng cho TẤT CẢ các script mở GPM:
1. **Lúc khởi động (`profiles/start/{pid}`):** Bắt buộc lưu ngay `process_id` từ JSON trả về:
   ```python
   r_start = requests.get(f"{GPM_BASE}/profiles/start/{pid}?win_scale=0.8", timeout=25).json()
   proc_id = r_start.get("data", {}).get("process_id")
   ```
2. **Lúc kết thúc (`finally:` block):**
   - Bước 1: Gửi API `GET /api/v3/profiles/stop/{pid}` để GPM cập nhật trạng thái nội bộ.
   - Bước 2: Dùng `psutil` **truy sát và force-kill toàn bộ cây tiến trình (mẹ + toàn bộ children)**:
   ```python
   finally:
       try:
           requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
       except Exception:
           pass
       if proc_id:
           try:
               proc = psutil.Process(proc_id)
               for child in proc.children(recursive=True):
                   try: child.kill()
                   except Exception: pass
               proc.kill()
           except (psutil.NoSuchProcess, psutil.AccessDenied):
               pass
   ```
3. **Quy tắc bất biến (Max 1 Active Profile):** Tuyệt đối không mở profile thứ 2 khi profile thứ 1 chưa được xác nhận đã chết hoàn toàn khỏi danh sách tiến trình của OS.

---

## 3. Code Mẫu Chuẩn (Standard Implementation)

```python
import os
import re
import time
import logging
from typing import Dict, Any, Optional
import requests

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("auto_gpm.client")

def stop_profile(self, profile_id: str, remote_port: Optional[int] = None) -> Dict[str, Any]:
    """Đóng profile trình duyệt đang chạy và dọn dẹp tiến trình nếu kẹt."""
    profile_path = None
    try:
        prof_info = self.get_profile(profile_id)
        if prof_info and prof_info.get("data"):
            profile_path = prof_info["data"].get("profile_path")
    except requests.RequestException as e:
        logger.debug(f"Không lấy được profile_path cho {profile_id}: {e}")

    api_err = None
    data = {}
    try:
        res = requests.get(f"{self.base_url}/profiles/stop/{profile_id}", timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        api_err = e

    # Kiểm tra và dọn dẹp nếu tiến trình Chrome tương ứng vẫn còn chạy
    if psutil is not None and profile_path and remote_port is not None and isinstance(remote_port, int) and 0 < remote_port <= 65535:
        try:
            # Chờ để Chrome đóng nhẹ nhàng nếu API thành công
            if api_err is None:
                time.sleep(1.0)

            target_port_flag = rf"^--remote-debugging-port={remote_port}$"
            norm_target_path = os.path.normpath(profile_path).lower()

            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if p.info['name'] and 'chrome' in p.info['name'].lower():
                        cmdline = p.info.get('cmdline') or []
                        has_port = any(re.match(target_port_flag, arg) for arg in cmdline)
                        has_profile = False
                        for arg in cmdline:
                            if arg.startswith("--user-data-dir="):
                                val = arg.split("=", 1)[1].strip('"\'')
                                norm_val = os.path.normpath(val).lower()
                                if norm_val == norm_target_path or norm_val.endswith(os.sep + norm_target_path):
                                    has_profile = True
                                    break

                        if has_port and has_profile:
                            p.terminate()
                            try:
                                p.wait(timeout=2.0)
                            except Exception:
                                p.kill()
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Lỗi khi dọn dẹp tiến trình Chrome cổng {remote_port}: {e}")

    if api_err:
        raise api_err

    return data
```

---

## 4. Áp dụng trong Batch Scripts

Trong các batch script (như `batch_chatgpt_priority.py`), luôn khởi tạo `remote_addr = None` ngoài khối `try`, và trong khối `finally:` luôn truyền `remote_addr` vào `stop_profile`:

```python
remote_addr = None
try:
    remote_addr = start_profile(profile_id)
    # ... thực hiện automation ...
finally:
    stop_profile(profile_id, port=remote_addr)
    time.sleep(2)
```
