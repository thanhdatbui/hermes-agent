# GPM Browser Lifecycle: Hard Process Cleanup, Anti-Spam & Concurrency Clamping

## 1. Nguyên nhân GPM Browser rò rỉ (Zombie Process Accumulation)
Khi tự động hóa GPMLogin trên PC qua Local API (port `19995`) và Playwright CDP:
- **Hiện tượng**: Hàng chục cửa sổ `chrome.exe` của GPM chạy ngầm dồn ứ (20–30+ process), ngốn sạch RAM/CPU và làm văng lỗi khi mở profile mới.
- **Nguyên nhân cốt lõi**:
  1. Hàm đóng profile chỉ gọi `requests.get(f"{GPM_BASE}/profiles/stop/{pid}")` hoặc `close`. Nếu Playwright gặp exception, disconnect, hoặc Chromium đang kẹt dialog/mạng, GPMLogin daemon **không kill được tiến trình con `chrome.exe`**.
  2. Cronjob cấu hình `MAX_WORKERS` quá cao (ví dụ: `MAX_WORKERS = 30`) và nổ hàng loạt worker cùng lúc không có độ trễ (stagger), làm nghẽn API GPM 19995 khiến các lệnh stop bị timeout hoặc drop.
  3. Thiếu khối `finally:` dọn dẹp dứt điểm ở cấp độ hệ điều hành.

---

## 2. Kỷ luật Bất biến: Hard Process Cleanup theo CDP Port
Mọi script mở GPM browser (dù là Login, Nuôi, 2FA hay Dual OAuth) **BẮT BUỘC** phải có khối dọn dẹp dứt điểm trong `finally:`.

### Quy chuẩn Code:
```python
import subprocess

def kill_chrome_by_port(port: int):
    """
    Force kill chính xác tiến trình Chrome gắn với target CDP port.
    Bảo vệ 100% Chrome cá nhân của User (không đụng tới Chrome không mang port GPM).
    """
    if not port or port in (9222,):
        return
    ps_cmd = (
        f"Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | "
        f"Where-Object {{ $_.CommandLine -match '{port}' }} | "
        f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=10)
    except Exception:
        pass
```

### Triển khai trong Luồng Automation:
```python
addr = start_gpm_profile(profile_id)
remote_port = int(addr.split(":")[-1]) if addr else None

try:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://{addr}", timeout=15000)
        # Thực thi logic...
finally:
    # 1. Báo cho GPM daemon đóng profile
    try:
        requests.get(f"{GPM_API_BASE}/profiles/stop/{profile_id}", timeout=10)
    except Exception:
        pass
    # 2. Hard kill process Chrome nếu vẫn còn sót lại trên port
    if remote_port:
        kill_chrome_by_port(remote_port)
```

---

## 3. Quy tắc Concurrency Clamping & Stagger
Để chống dồn ứ và nghẽn hệ thống:
1. **Clamp MAX_WORKERS**: Mọi cronjob tương tác với GPM browser chỉ được chạy tối đa **`MAX_WORKERS = 2`** (tối đa 3 nếu tác vụ siêu nhẹ, CẤM TUYỆT ĐỐI để 10, 20 hay 30).
2. **Stagger bắt buộc**: Khi submit task vào `ThreadPoolExecutor`, bắt buộc giãn cách `time.sleep(3)` đến `time.sleep(5)` giữa các worker:
   ```python
   with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
       futures = []
       for item in eligible:
           futures.append(executor.submit(_process_single, item))
           time.sleep(3)  # Giãn cách chống nghẽn Local API GPM
       for f in as_completed(futures):
           ...
   ```

---

## 4. Chỉ thị Vận hành: "K pause sửa code"
Khi phát hiện cronjob spam tiến trình hoặc gây kẹt trình duyệt:
- **CẤM TUYỆT ĐỐI**: Tự ý `cronjob action='pause'` hoặc vô hiệu hóa cronjob của hệ sinh thái farm (vì làm gián đoạn lịch trình tự động toàn diện).
- **HÀNH ĐỘNG ĐÚNG**:
  1. Truy vết O(1) tìm đích danh cronjob và script gây lỗi.
  2. Kill sạch tiến trình rác hiện trường ngay lập tức qua PowerShell:
     `Get-Process chrome | Where-Object { $_.Path -match 'gpm_browser' } | Stop-Process -Force`
  3. Sửa thẳng vào code: Hạ `MAX_WORKERS`, thêm stagger và chèn hard kill `kill_chrome_by_port` trong `finally:`.
  4. Đồng bộ ngay sang cả runtime (`AppData/Local/hermes/scripts`) và deploy repo (`deploy/hermes-home/scripts`).

---

## 5. Cạm bẫy Ký tự Thoát Đường dẫn Windows (Control Character `\x07`)
Trong code Python định nghĩa đường dẫn Windows:
- **Pitfall**: Viết chuỗi thông thường `"D:\Taadaa\automation-core\src"` khiến `\a` bị Python parse thành ký tự điều khiển ASCII Bell (`\x07`), dẫn tới `sys.path` trỏ tới path rác `D:\Taadaa\x07utomation-core\src`, gây `ImportError` âm thầm.
- **Quy chuẩn**: Luôn dùng raw string `r"D:\Taadaa\automation-core\src"` hoặc dấu gạch xuôi chuẩn POSIX `"D:/Taadaa/automation-core/src"`.
