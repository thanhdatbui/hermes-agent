# GPM Profile Backup Preflight & Lock Release Protocol

## 1. Bối cảnh & Hiện tượng File Lock khi Backup (`[Errno 13] Permission denied`)

Khi chạy cronjob hoặc script sao lưu định kỳ thư mục profiles của GPMLogin (`Default/Network/Cookies`, `Login Data`, SQLite DB):
- Chromium giữ exclusive lock (khóa độc quyền) đối với các file SQLite và file mạng `Cookies` trong suốt thời gian profile còn đang mở.
- Nếu backup chạy trong lúc có tác vụ nuôi tài khoản, reg ChatGPT hoặc nạp OAuth đang mở profile, thao tác đọc file sẽ văng lỗi:
  ```text
  Lock/Read error on Default/Network/Cookies in <profile_path>: [Errno 13] Permission denied
  ```
- **Hậu quả:** File backup thiếu cookies quan trọng khiến phiên đăng nhập không toàn vẹn khi restore, đồng thời phát sinh cảnh báo lỗi rác trên báo cáo tự động.

---

## 2. Quy tắc Pre-Backup Bắt buộc: Đóng Profile Trước Khi Sao Lưu

User chỉ đạo nhất quán: **"Trước khi chạy backup thì đóng hết profile đi để không có lỗi."**
Mọi quy trình backup profile GPM (one-off hoặc cronjob hàng tuần) **BẮT BUỘC** gọi hàm dọn dẹp trước khi bắt đầu copy DB hoặc nén zip:

### A. Quy trình 3 pha tiêu chuẩn
1. **Pha 1: Graceful Stop qua GPM Local API (`http://127.0.0.1:19995`)**
   - Query danh sách profile: `GET /api/v3/profiles`.
   - Với mỗi profile có trạng thái `running` / `open` / `1` / `True`: gọi `GET /api/v3/profiles/stop/{profile_id}`.
   - Cho phép Chromium flush hoàn toàn session, local storage và cookies về đĩa cứng một cách êm ái.
2. **Pha 2: Quét dọn tiến trình sót qua `psutil` (Targeted Cleanup)**
   - Quét các tiến trình `chrome.exe`, `gpm.exe`, `gpmlogin.exe`.
   - **Bộ lọc bắt buộc (Ironclad Guard):**
     + `cmdline` PHẢI chứa marker thư mục profile GPM: `gpmlogin\\profile` hoặc `programs\gpmlogin\profile`.
     + **CẤM TUYỆT ĐỐI** đụng tới Chrome cá nhân của User: nếu `cmdline` chứa `google\chrome\user data` ➔ BỎ QUA NGAY.
     + **CẤM TUYỆT ĐỐI** can thiệp vào các tiến trình hệ thống farm: `python`, `hermes`, `adb`, `xiaowei`.
   - Gửi tín hiệu `terminate()` để dọn dẹp các instance mồ côi.
3. **Pha 3: Settle Delay (Chờ giải phóng File Lock)**
   - Windows kernel cần thời gian để đóng socket handle và file descriptor.
   - BẮT BUỘC gọi `time.sleep(2.0)` trước khi bắt đầu đọc file hoặc snapshot SQLite database.

---

## 3. Template Mẫu Chuẩn: `close_all_running_gpm_profiles()`

```python
import time
import logging
import requests
import psutil

logger = logging.getLogger("gpm_backup")

def close_all_running_gpm_profiles(gpm_api_url: str = "http://127.0.0.1:19995", settle_delay: float = 2.0) -> int:
    """
    Đóng toàn bộ GPM profiles đang mở trước khi backup để giải phóng triệt để file lock.
    """
    closed_count = 0

    # 1. Graceful shutdown via GPM API
    try:
        res = requests.get(f"{gpm_api_url}/api/v3/profiles", timeout=3)
        if res.status_code == 200:
            profiles = res.json().get("data", [])
            for p in profiles:
                pid = p.get("id") or p.get("profile_id")
                if p.get("status") in ("running", "open", 1, True) and pid:
                    try:
                        requests.get(f"{gpm_api_url}/api/v3/profiles/stop/{pid}", timeout=3)
                        closed_count += 1
                        logger.info(f"Đã đóng graceful GPM profile {pid} qua API")
                    except Exception as e:
                        logger.warning(f"Lỗi khi dừng profile {pid} qua API: {e}")
    except Exception as e:
        logger.info(f"GPM API không khả dụng hoặc timeout ({e}); chuyển sang rà soát tiến trình")

    # 2. Targeted cleanup via psutil
    gpm_marker = r"appdata\local\programs\gpmlogin\profile"
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline_list = proc.info.get('cmdline') or []
            cmdline_str = " ".join(cmdline_list).lower()
            name = (proc.info.get('name') or "").lower()

            # Bảo vệ Chrome cá nhân & tiến trình farm
            if "google\\chrome\\user data" in cmdline_str:
                continue
            if any(k in name for k in ("python", "hermes", "adb", "node", "xiaowei")):
                continue

            if gpm_marker in cmdline_str:
                logger.info(f"Dọn dẹp process GPM sót PID {proc.pid}: {name}")
                proc.terminate()
                closed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if closed_count > 0:
        logger.info(f"Đã đóng {closed_count} profile GPM. Chờ {settle_delay}s nhả lock...")
    time.sleep(settle_delay)
    return closed_count
```

---

## 4. Kiểm thử Đơn vị & Mocking Khuyến nghị

Khi viết unit test cho preflight đóng profile:
- Mock `requests.get` để giả lập response `200` có danh sách profiles running và trả về success cho endpoint `/stop/{id}`.
- Mock `psutil.process_iter` với 2 process giả lập: 1 process GPM (có path `gpmlogin\profile`) và 1 process User Chrome (có path `google\chrome\user data`) để kiểm chứng rào chắn không kill nhầm Chrome cá nhân.
