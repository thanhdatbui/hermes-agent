# GPMLogin API `/profiles/stop` Browser Zombie & Taskbar Spam Trap

> 📌 **Bối cảnh thực tế (Sự cố Taskbar Spam):**  
> Khi User đang làm việc hoặc render video nặng (ví dụ CapCut PC), hàng loạt cửa sổ Chromium GPM bất ngờ xuất hiện và tràn ngập Taskbar Windows (thực tế ghi nhận 48+ cửa sổ liên tiếp với badge 94–147). Nguyên nhân do script audit/lifecycle chạy ngầm (`login_audit_and_purge_deactivated.py`) mở profile qua GPM CDP để kiểm tra từng tài khoản, nhưng không dọn sạch tiến trình browser sau khi kiểm tra xong.

---

## 1. Bản Chất Kỹ Thuật: Khiếm Khuyết Của GPM Local API `/profiles/stop`

### 1.1 GPM API `stop` Không Tự Động Kill `chrome.exe` Trên Windows
- Khi gọi `GET /api/v3/profiles/stop/{id}`, GPMLogin Local API (port 19995) trả về:
  ```json
  {
    "success": true,
    "data": { "id": "...", "profile_path": "..." },
    "message": "OK"
  }
  ```
- **Thực tế hệ điều hành**: API này chỉ cập nhật cờ trạng thái nội bộ của app GPMLogin và gửi tín hiệu đóng qua websocket/driver. Nếu trình duyệt đang có CDP session mở, trang web đang loading, hoặc tiến trình con bị treo:
  - **Tiến trình `chrome.exe` và cửa sổ UI KHÔNG BỊ TERMINATE**.
  - Cửa sổ Chromium vẫn tồn tại nguyên vẹn trên màn hình và Taskbar.

### 1.2 Hiệu Ứng Tuyết Lăn (Cascade Spam) Trong Các Vòng Lặp Audit
- Trong các script duyệt danh sách tài khoản (ví dụ duyệt 70 Hotmail):
  ```python
  # ❌ BẪY CHÍ MẠNG: Chỉ gọi GPM stop API rồi bỏ mặc
  try:
      host_port = _start_gpm_profile(profile_id, timeout)
      ... # kiểm tra đăng nhập / OTP qua CDP
  finally:
      _stop_gpm_profile(profile_id)  # Chỉ gửi HTTP GET /profiles/stop
  ```
- **Hậu quả**: Vòng lặp chạy qua 70 tài khoản $\rightarrow$ Mỗi vòng lặp đẻ thêm 1 cửa sổ trình duyệt mới $\rightarrow$ Taskbar bị spam 50–70 cửa sổ đè kín màn hình, nuốt cạn RAM và làm giật lag máy User.

---

## 2. Quy Chuẩn Đóng Profile Bắt Buộc: Dual-Stop Pattern (API + Psutil Force-Kill)

Mọi script tự động hóa mở GPM Profile (audit, login, reg, 2FA) **BẮT BUỘC** áp dụng cơ chế đóng kép 2 bước:

```python
import os
import time
import requests
import psutil

def safe_stop_gpm_profile(profile_id: str, profile_path: str = None, api_base: str = "http://127.0.0.1:19995/api/v3"):
    """
    Dual-Stop:
    1. Báo GPM API stop để đồng bộ database / trạng thái UI.
    2. Quét psutil để terminate & kill triệt để process tree của browser profile đó.
    """
    # Bước 1: Gửi lệnh stop tới GPM Local API
    try:
        requests.get(f"{api_base}/profiles/stop/{profile_id}", timeout=5)
    except Exception as exc:
        logger.debug(f"GPM stop API error for {profile_id}: {exc}")

    time.sleep(1.0)

    # Bước 2: Force-kill tiến trình Chrome của đúng profile này bằng psutil
    if not profile_path:
        return

    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = p.info.get('cmdline') or []
            cmd_str = " ".join(cmdline).lower()

            # Bảo vệ tuyệt đối Chrome cá nhân của User
            if "google\\chrome\\user data" in cmd_str:
                continue

            # Chỉ nhắm vào tiến trình gpm_browser chứa profile_path tương ứng
            if "gpm_browser" in cmd_str and profile_path.lower() in cmd_str:
                # Terminate tiến trình mẹ và toàn bộ con
                try:
                    for child in p.children(recursive=True):
                        child.kill()
                except Exception:
                    pass
                p.terminate()
                try:
                    p.wait(timeout=1.0)
                except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                    p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
```

---

## 3. Van An Toàn Concurrency Cap Cho Các Script Lặp

### 3.1 Hard Gate: Concurrency Cap Kiểm Tra Tiến Trình Thực Tế
Trước khi khởi động profile tiếp theo trong bất kỳ vòng lặp nào (kể cả serial hay batch), script **BẮT BUỘC** đếm số lượng tiến trình GPM Chrome mẹ đang chạy:

```python
def count_active_gpm_browsers() -> int:
    cnt = 0
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            name = (p.info.get('name') or '').lower()
            cmd = p.info.get('cmdline') or []
            if 'chrome' in name and any('gpm_browser' in a for a in cmd) and not any(a.startswith('--type=') for a in cmd):
                cnt += 1
        except Exception:
            continue
    return cnt

# Trong vòng lặp:
active = count_active_gpm_browsers()
if active >= MAX_CONCURRENCY:  # 1 đối với script audit tuần tự, 5 đối với supervisor
    # Tạm dừng hoặc dọn dẹp trước khi spawn tiếp, cấm mở thêm bừa bãi
```

### 3.2 Triage Khẩn Cấp Khi Phát Hiện Spam Taskbar
Khi nhận alert hoặc khiếu nại của User về việc Taskbar bị spam cửa sổ profile:
1. **Dọn sạch ngay lập tức bằng watchdog mode threshold 0**:
   ```bash
   python D:/Taadaa/Hermes/deploy/hermes-home/scripts/gpm_stale_profile_watchdog.py --threshold 0
   ```
   *Lệnh này đóng API + kill toàn bộ GPM Chrome treo nhưng bảo vệ 100% Chrome cá nhân của User.*
2. **Kiểm tra tiến trình cha phát tán**:
   - Truy tìm các script audit/healer chạy ngầm (`psutil` cmdline).
   - Kill script nguồn và tạm dừng (pause) cronjob tương ứng (`cronjob action='pause' job_id=...`).
