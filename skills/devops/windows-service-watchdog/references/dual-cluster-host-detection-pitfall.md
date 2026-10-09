# Multi-Host Watchdog Host Detection Pitfall & OS-Level Discrimination

## 1. Vấn đề phát sinh (The Bug)

Trong kiến trúc farm đa cụm (Dual-Cluster: Controller PC `Kibe` vs Remote Host `Admin`), một script watchdog dùng chung (`farm_render_download_watchdog.py`) được triển khai lên cả hai máy.

Nếu script xác định máy chủ hiện tại bằng cách kiểm tra sự tồn tại của thư mục trên ổ đĩa:
```python
# CODE LỖI (ANTI-PATTERN):
def detect_host():
    if os.path.exists(r"D:\video goc may 2") or os.environ.get("TAADAA_HOST", "").lower() == "admin":
        return {"name": "FARM ADMIN", ...}
    return {"name": "FARM KIBE", ...}
```

### Hậu quả nghiêm trọng:
1. Khi máy Controller (`Kibe`) có một thư mục test cũ hoặc thư mục backup/sync tên `D:\video goc may 2`, điều kiện `os.path.exists()` trả về `True`.
2. Script chạy trên máy Kibe nhưng lại nhận nhầm mình là `FARM ADMIN`.
3. Script thực thi nhánh logic của Admin: chỉ lấy dữ liệu `D:\TIKTOK-videonuoinick-admin`, bỏ qua hoàn toàn cụm Kibe (`D:\TIKTOK-videonuoinick`).
4. Khi cronjob chạy trên Kibe bắn report về Telegram Farm Alert, người dùng chỉ thấy báo cáo của Admin mà **không hề thấy báo cáo của Kibe**, gây hoang mang và hiểu lầm là farm Kibe đã bị crash hoặc ngừng chạy.

---

## 2. Giải pháp kỹ thuật chuẩn hóa (The Fix)

**NGUYÊN TẮC BẤT BIẾN**: Tuyệt đối không dùng sự tồn tại của file/folder đĩa (`os.path.exists`) làm tiêu chí phân biệt Host giữa các máy, vì các thư mục có thể được tạo tạm, đồng bộ qua OneDrive, hoặc sao chép qua mạng LAN.

BẮT BUỘC sử dụng thông tin định danh hệ điều hành (OS Identity) độc nhất:

```python
import os
import getpass
import socket

def detect_host():
    # 1. Định danh theo Windows USERNAME
    user = os.environ.get("USERNAME", "").lower() or getpass.getuser().lower()
    host_env = os.environ.get("TAADAA_HOST", "").lower()
    hostname = socket.gethostname().lower()

    if user == "admin" or host_env == "admin" or "admin" in hostname:
        return {
            "name": "FARM ADMIN",
            "video_goc": r"D:\video goc may 2",
            "render_root": r"D:\TIKTOK-videonuoinick-admin",
            "state_db": r"D:\CodexRuntime\tiktok-video-machine2\state.db",
            "machine_range": range(201, 281),
            "base_machine": 201,
        }

    # Mặc định là Controller Kibe
    return {
        "name": "FARM KIBE",
        "video_goc": r"D:\video goc",
        "render_root": r"D:\TIKTOK-videonuoinick",
        "state_db": r"C:\CodexRuntime\tiktok-video\state.db",
        "machine_range": range(1, 81),
        "base_machine": 1,
    }
```

---

## 3. Quy tắc đồng bộ Dual-Cluster Watchdog

1. Khi sửa watchdog dùng chung trên Controller (`Kibe`), phải đồng bộ đủ 4 điểm:
   - Local runtime: `%LOCALAPPDATA%\hermes\scripts\`
   - Git Master deploy: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`
   - Shared Sync: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`
   - Remote Host qua SSH/SCP: `admin-farm:%LOCALAPPDATA%\hermes\scripts\`
2. Sau khi sửa, BẮT BUỘC chạy thử trực tiếp trên local host và gọi `cronjob(action='run', job_id=...)` để kiểm chứng bản tin gửi về Telegram trước khi chốt.
