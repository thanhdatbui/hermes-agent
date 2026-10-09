# Clean Chrome / GPM Profile Process Shutdown Pattern

Khi chạy batch automation với số lượng lớn profile GPM (GPMLogin API v3), việc chỉ gọi REST API `/profiles/stop/{profile_id}` thường không đảm bảo đóng hoàn toàn 100% các tiến trình Chrome.
Các nguyên nhân phổ biến:
1. GPM API timeout hoặc phản hồi `success: true` nhưng Chrome driver/browser renderer bị treo ngầm.
2. Zombie `chrome.exe` chiếm dụng port Remote Debugging CDP cũ hoặc giữ lock thư mục profile data.
3. Rò rỉ RAM và CPU khi chạy đồng thời nhiều worker (ThreadPoolExecutor).

---

## 1. Nguyên tắc 2 lớp (Two-tier Teardown)

Mỗi khi đóng profile GPM, luôn thực thi 2 bước:
1. **Lớp 1 (Graceful stop qua GPM API):** Gửi yêu cầu `/profiles/stop/{profile_id}` để GPM cập nhật trạng thái UI và flush profile data.
2. **Lớp 2 (Force kill theo Remote Debugging Port qua `psutil`):** Quét các tiến trình `chrome.exe` hoặc `gpmdriver.exe` có command-line chứa chính xác `--remote-debugging-port=<port>` để diệt dứt điểm.

---

## 2. Mã nguồn mẫu chuẩn (Standard Snippet)

```python
import logging
from typing import Optional, Union
import requests
import psutil

logger = logging.getLogger("gpm.teardown")

def kill_chrome_by_port(port: Union[int, str]) -> int:
    """Quét và kill triệt để Chrome instance đang lắng nghe trên CDP port cụ thể."""
    if not port:
        return 0
    port_str = str(port).strip()
    if ":" in port_str:
        port_str = port_str.split(":")[-1]
    
    killed = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = (proc.info.get('name') or '').lower()
            if 'chrome' in name or 'gpmdriver' in name:
                cmd = ' '.join(proc.info.get('cmdline') or [])
                if f'--remote-debugging-port={port_str}' in cmd or f':{port_str}' in cmd:
                    proc.kill()
                    killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except Exception as e:
            logger.debug(f"Error inspecting proc {proc}: {e}")
            
    if killed:
        logger.info(f"Đã dọn dẹp triệt để {killed} tiến trình Chrome trên port {port_str}")
    return killed

def stop_profile_thoroughly(base_url: str, profile_id: str, remote_addr_or_port: Optional[Union[str, int]] = None, timeout: int = 15):
    """Đóng profile qua GPM API và kill process theo port CDP."""
    # Bước 1: GPM API stop
    try:
        requests.get(f"{base_url}/profiles/stop/{profile_id}", timeout=timeout)
    except Exception as e:
        logger.warning(f"Lỗi khi gọi API stop profile {profile_id}: {e}")

    # Bước 2: Force kill nếu có thông tin port
    if remote_addr_or_port:
        kill_chrome_by_port(remote_addr_or_port)
```

---

## 3. Lưu ý sống còn trong Batch Script
* Luôn khai báo `remote_addr = None` bên ngoài khối `try:` trong worker function.
* Luôn truyền `remote_addr` vào khối `finally:` để đảm bảo dù code gãy ở bất kỳ bước nào (kết nối CDP thất bại, timeout điều hướng, exception bất ngờ) thì Chrome instance sinh ra vẫn được thu hồi sạch sẽ.
