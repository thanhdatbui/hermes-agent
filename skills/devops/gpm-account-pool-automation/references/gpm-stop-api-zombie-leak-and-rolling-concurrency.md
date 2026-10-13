# GPM Stop API Zombie Process Leak & Rolling Concurrency Pattern

## 1. GPM Local API /stop Zombie Process Leak on Windows

### Triệu chứng & Nguyên nhân
- Khi gọi endpoint GPM Local API `GET /api/v3/profiles/stop/{profile_id}` trên Windows, API trả về `{"success": true, "message": "OK"}` nhưng **không thực sự kill tiến trình `chrome.exe`**.
- Trong các script chạy hàng loạt (audit, purge, login, nurture), nếu chỉ tin tưởng vào API `/stop`, mỗi profile mở ra sẽ bị bỏ rơi thành một tiến trình mồ côi (zombie process). Sau vài chục tài khoản, taskbar sẽ bị spam hàng chục đến hàng trăm cửa sổ Chromium, đè nghẹt CPU/RAM và làm treo máy.

### Quy chuẩn xử lý dứt điểm (Process Termination via psutil)
Sau khi gọi GPM `/stop` API, bắt buộc phải có bước dọn dẹp cấp hệ điều hành bằng `psutil`:
1. **Lấy debugging port:** Khi mở profile qua `/start`, GPM trả về CDP address (ví dụ `127.0.0.1:54321`), trích xuất port này.
2. **Bảo vệ tuyệt đối Chrome cá nhân:** Trước khi kiểm tra hoặc kill, BẮT BUỘC bỏ qua mọi tiến trình có command line chứa `Google\Chrome\User Data` hoặc `google/chrome/user data`.
3. **Kill theo port và process tree:** Tìm tiến trình Chrome có `--remote-debugging-port=<port>` (hoặc khớp profile-path trong `gpmlogin/profile`), terminate/kill process mẹ và toàn bộ `p.children(recursive=True)`.

```python
def _kill_gpm_chrome(host_port):
    if not host_port or psutil is None:
        return
    port = str(host_port).split(":")[-1]
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            cmd = " ".join(p.info.get('cmdline') or []).lower()
            if "google\\chrome\\user data" in cmd or "google/chrome/user data" in cmd:
                continue
            if f"--remote-debugging-port={port}" in cmd:
                for c in p.children(recursive=True):
                    c.kill()
                p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
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
