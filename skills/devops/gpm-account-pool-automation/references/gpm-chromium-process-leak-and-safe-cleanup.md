# Khắc Phục Rò Rỉ Tiến Trình Chromium GPMLogin & Quy Tắc Dọn Dẹp An Toàn

## 1. Bản Chất Sự Cố Rò Rỉ Tiến Trình (Chromium Process Leak)
Trong các tác vụ tự động hóa GPMLogin (nuôi Gmail, add 2FA, OAuth Antigravity/Codex, reg ChatGPT), việc hàng trăm tiến trình Chrome/Chromium bị kẹt mồ côi (orphaned) trên Taskbar sau nhiều giờ chạy thường xuất phát từ 2 lỗi cốt lõi:

### Lỗi 1: `kill_chrome_by_port` bỏ sót toàn bộ cây tiến trình con
- Khi Chromium khởi động với `--remote-debugging-port=PORT`, chỉ duy nhất **tiến trình mẹ (browser main process)** mang tham số cổng này trong Command Line.
- Các tiến trình con gồm: `type=renderer` (các tab, iframe), `type=gpu-process`, `type=utility` (network service, audio service, crashpad handler) **KHÔNG hề chứa tham số `--remote-debugging-port`**.
- Do đó, lệnh lọc tiến trình kiểu:
  ```powershell
  Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '$port' } | Stop-Process -Force
  ```
  chỉ tiêu diệt được đúng 1 tiến trình mẹ! Hàng chục tiến trình con renderer và GPU bị cắt đứt liên lạc, trở thành process mồ côi bám chặt RAM và Taskbar, tích lũy qua từng profile lên tới 400-500 tiến trình.

### Lỗi 2: Bất đối xứng giữa endpoint `/stop` và `/close` của GPMLogin API v3
- Một số phiên bản GPMLogin v3/v4 xử lý endpoint `/profiles/stop/{id}` và `/profiles/close/{id}` khác nhau:
  - Một số phiên bản chỉ giải phóng port CDP nhưng không đóng cửa sổ (`stop`).
  - Một số phiên bản đóng window nhưng không unregister profile trạng thái đang chạy trong local database (`close`).
- **Quy tắc bắt buộc**: Phải gọi fallback cả hai endpoint: `/profiles/close/{id}` và `/profiles/stop/{id}`.

---

## 2. Quy Tắc Bất Biến: Bảo Vệ Tuyệt Đối Chrome Cá Nhân Của Người Dùng
Người dùng thường xuyên mở trình duyệt Google Chrome chính chủ (`C:\Program Files\Google\Chrome\Application\chrome.exe`) để làm việc, check tin nhắn, lướt web.
Mọi lệnh force-kill tiến trình Chrome **CẤM TUYỆT ĐỐI** dùng lệnh quét tên chung chung như `Stop-Process -Name chrome` hay lọc bare `chrome.exe` mà không có guardrail.

### Điều kiện lọc bắt buộc:
1. **Phải kiểm tra nguồn gốc GPMLogin**:
   - `CommandLine -like '*GPMLogin*'` hoặc `CommandLine -like '*gpm_browser*'`.
   - Nếu dùng `psutil`: duyệt `cmdline` và kiểm tra `'gpmlogin' in arg.lower()`.
2. **So khớp mục tiêu**:
   - Khớp `--user-data-dir` chứa đường dẫn thư mục profile (hoặc profile ID).
   - Khớp tham số `--remote-debugging-port`.
   - Khớp chuỗi profile ID trong commandline.

---

## 3. Công Thức Chuẩn (Standard Patterns)

### Pattern 1: PowerShell CIM Query (Nhanh & Triệt Để)
```powershell
$profId = "<profile_id>"
$port = "<port>"
Get-CimInstance Win32_Process | Where-Object {
    ($_.CommandLine -like '*GPMLogin*') -and
    (($_.CommandLine -like "*$profId*") -or ($_.CommandLine -match "--remote-debugging-port=$port"))
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
```

### Pattern 2: Python psutil (Trong `gpm_client.py`)
```python
# Gọi cả 2 endpoint đóng
for endpoint in ["close", "stop"]:
    try:
        requests.get(f"{self.base_url}/profiles/{endpoint}/{profile_id}", timeout=self.timeout)
    except Exception:
        pass

# Force-kill sạch tiến trình con còn kẹt
if psutil is not None:
    try:
        time.sleep(1.0)
        clean_pid = profile_id.lower()
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                p_name = (p.info.get('name') or '').lower()
                if 'chrome' in p_name:
                    cmdline = p.info.get('cmdline') or []
                    # BẢO VỆ CHROME CÁ NHÂN
                    if not any('gpmlogin' in arg.lower() for arg in cmdline):
                        continue

                    # So khớp profile ID hoặc port
                    match = any(clean_pid in arg.lower() for arg in cmdline)
                    if not match and remote_port:
                        match = any(f"--remote-debugging-port={remote_port}" in arg for arg in cmdline)

                    if match:
                        p.terminate()
                        try:
                            p.wait(timeout=1.5)
                        except Exception:
                            p.kill()
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Lỗi dọn dẹp profile {profile_id}: {e}")
```

### Pattern 3: Khối `finally` an toàn trong kịch bản Playwright CDP
```python
finally:
    if browser:
        try: browser.close()
        except Exception: pass
    if pw:
        try: pw.stop()
        except Exception: pass
    for endpoint in ["close", "stop"]:
        try:
            requests.get(f"{GPM_BASE}/profiles/{endpoint}/{pid}", timeout=10)
        except Exception: pass
    time.sleep(1)
    kill_chrome_by_port(port, pid)
```

---

## 4. Cảnh Báo Điều Phối Subagent Khi Sửa Code & Test
1. **Cấm chạy repo-wide `pytest` trên repo lớn**:
   - Khi giao việc cho worker subagent, cấm để subagent chạy lệnh test diện rộng `pytest "D:/Taadaa/GPM auto"`. Việc này quét hàng chục test suite không liên quan, bị timeout 180s và làm cạn kiệt budget lượt gọi.
   - Chỉ được chạy kiểm tra cú pháp trọng tâm `python -m py_compile <các_file_sửa>` hoặc chạy unit test đích danh dưới 30s.
2. **Cẩn trọng với ký tự escape lồng nhau**:
   - Tránh dùng `strip('"\'')` lồng sâu trong chuỗi lệnh bash `-c` vì sẽ gây lỗi cú pháp parser bash/Python. Hãy thay bằng `.replace('"', '').replace("'", "")`.
