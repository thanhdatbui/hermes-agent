# GPM Stop API Zombie Process Leak & Rolling Concurrency Pattern

## 1. GPM Local API /stop Zombie Process Leak on Windows

### Triệu chứng & Nguyên nhân
- Khi gọi endpoint GPM Local API `GET /api/v3/profiles/stop/{profile_id}` trên Windows, API trả về `{"success": true, "message": "OK"}` nhưng **không thực sự kill tiến trình `chrome.exe`**.
- Trong các script chạy hàng loạt (audit, purge, login, nurture), nếu chỉ tin tưởng vào API `/stop`, mỗi profile mở ra sẽ bị bỏ rơi thành một tiến trình mồ côi (zombie process). Sau vài chục tài khoản, taskbar sẽ bị spam hàng chục đến hàng trăm cửa sổ Chromium, đè nghẹt CPU/RAM và làm treo máy.

### Quy chuẩn xử lý dứt điểm (Process Termination via psutil)
Sau khi gọi GPM `/stop` API, bắt buộc phải có bước dọn dẹp cấp hệ điều hành bằng `psutil`:
1. **Lấy debugging port hoặc profile_id:** Khi mở profile qua `/start`, GPM trả về CDP address (ví dụ `127.0.0.1:54321`), trích xuất port này hoặc profile_id tương ứng.
2. **CẢNH BÁO BẪY `p.info['name']`:** Trên Windows, tên tiến trình trong Task Manager / `p.info['name']` luôn là **`chrome.exe`**, TUYỆT ĐỐI KHÔNG kiểm tra `if 'gpm_browser' in p.info['name']` (sẽ không bao giờ match và bỏ sót 100% tiến trình mồ côi!). Chuỗi `gpm_browser` chỉ nằm trong đường dẫn file thực thi `exe` hoặc `cmdline`.
3. **Bảo vệ tuyệt đối Chrome cá nhân:** Trước khi kiểm tra hoặc kill, BẮT BUỘC bỏ qua mọi tiến trình có command line chứa `Google\Chrome\User Data` hoặc `google/chrome/user data`.
4. **Kill theo port và process tree:** Tìm tiến trình Chrome có `--remote-debugging-port=<port>` hoặc `--user-data-dir` khớp profile ID/path trong `gpmlogin/profile`, terminate/kill process mẹ và toàn bộ `p.children(recursive=True)`.

```python
def _kill_gpm_chrome(host_port=None, profile_id=None):
    if psutil is None:
        return
    port = str(host_port).split(":")[-1] if host_port else None
    for p in psutil.process_iter(['name', 'cmdline', 'exe']):
        try:
            if 'chrome' not in (p.info.get('name') or '').lower():
                continue
            cmd = " ".join(p.info.get('cmdline') or []).lower()
            norm_cmd = cmd.replace("/", "\\")
            if "google\\chrome\\user data" in norm_cmd:
                continue  # Bảo vệ Chrome cá nhân
            
            should_kill = False
            if port and f"--remote-debugging-port={port}" in cmd:
                should_kill = True
            elif profile_id and profile_id.lower() in cmd and "gpmlogin" in norm_cmd:
                should_kill = True
                
            if should_kill:
                for c in p.children(recursive=True):
                    try: c.kill()
                    except Exception: pass
                p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
```

### 1.1. Phân biệt Số Tiến Trình (Processes) vs Số Cửa Sổ Profile (Main Profiles)
- **Kiến trúc Multi-Process của Chromium:** Mỗi 1 Profile/cửa sổ GPM khi khởi chạy sẽ spawn từ **6 đến 12 tiến trình con** độc lập trong Windows Task Manager (`chrome.exe`):
  * 1 Browser Process chính (`--user-data-dir=...`, không có cờ `--type=`)
  * 1 GPU Process (`--type=gpu-process`)
  * 1 Network Service (`--type=utility --utility-sub-type=network.mojom.NetworkService`)
  * 1 Storage Service (`--type=utility --utility-sub-type=storage.mojom.StorageControl`)
  * Renderer processes cho mỗi Tab / Iframe / Extension.
- **Quy tắc đếm Profile thực tế:** Khi User hoặc Watchdog kiểm tra số profile đang mở, **CẤM** lấy tổng số tiến trình `chrome.exe` (ví dụ 46 hay 160 tiến trình) để kết luận là có 46 hay 160 profile mở. Muốn đếm số profile thực sự đang chạy, BẮT BUỘC lọc:
  ```python
  main_profiles = [
      p for p in psutil.process_iter(['name', 'exe', 'cmdline'])
      if p.info['name'] and 'chrome' in p.info['name'].lower()
      and 'gpmlogin' in (p.info.get('exe') or '').lower()
      and not any('--type=' in a for a in (p.info.get('cmdline') or []))
  ]
  # len(main_profiles) chính là số profile thực tế đang mở!
  ```

---

## 2. Mô hình "Cuốn Chiếu" Chuẩn (Rolling Concurrency Pool)

### Định nghĩa "Cuốn Chiếu" theo yêu cầu người dùng
- **KHÔNG PHẢI tuần tự (sequential):** Chạy 1 acc xong mới tới acc tiếp theo (quá chậm, dễ tắc nghẽn).
- **KHÔNG PHẢI batch cố định:** Mở 5 acc cùng lúc rồi đứng chờ cả 5 acc hoàn tất mới mở 5 acc tiếp theo (lãng phí thời gian khi các acc có độ trễ lệch nhau).
- **LÀ ROLLING CONCURRENCY:** Luôn duy trì đúng $N$ active workers (mặc định $N = 5$). Bất kỳ worker nào xử lý xong 1 profile (và kill tiến trình dọn dẹp xong), worker đó lập tức bốc profile tiếp theo trong hàng đợi vào làm. 

### Lợi ích & An toàn
- Số lượng cửa sổ profile GPM trên màn hình / taskbar luôn $\le N$ tại mọi thời điểm, không spam giao diện người dùng.
- Tốc độ xử lý tối ưu liên tục (saturation), không có khoảng thời gian chết chờ đợi giữa các batch.

---

## 3. Template Triển Khai Chuẩn Python (Rolling Pool 5 Workers)

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_rolling_audit_pool(matched_targets, max_workers=5):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # submit toàn bộ task vào queue; ThreadPoolExecutor duy trì đúng max_workers chạy đồng thời
        future_to_acc = {
            executor.submit(verify_single_account, acc, pid): acc
            for acc, pid in matched_targets
        }
        for future in as_completed(future_to_acc):
            acc = future_to_acc[future]
            try:
                status, proof = future.result()
                results.append((acc["email"], status, proof))
                logger.info("[PROGRESS] %s: %s (Total completed: %d/%d)", acc["email"], status, len(results), len(matched_targets))
            except Exception as exc:
                logger.error("[ERROR] Task failed for %s: %s", acc["email"], exc)
                results.append((acc["email"], "ERROR", None))
            # Ghi nhận kết quả lũy tiến (Write-Through) để tránh mất dữ liệu nếu bị ngắt ngang
            _flush_intermediate_report(results)
    return results
```
*Lưu ý cốt lõi:* Trong hàm worker (`verify_single_account`), khối `finally` BẮT BUỘC phải gọi `_stop_gpm_profile(profile_id, host_port=host_port)` để dọn sạch tiến trình Chrome trước khi slot được nhả lại cho worker kế tiếp.
