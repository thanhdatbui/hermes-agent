# Kỷ luật Dọn dẹp Tiến trình Chromium GPMLogin & Bảo vệ Chrome Cá nhân

## 1. Bối cảnh & Nguyên nhân Gốc (Root Cause)
Khi vận hành batch automation hoặc cronjob với GPMLogin Local API (port 19995):
- **Hiện tượng rò rỉ**: Hàng trăm tiến trình con Chromium (`GPMLogin\gpm_browser\chrome.exe`) tích tụ âm thầm trên Taskbar và Background Processes (đã từng phát hiện rò rỉ hơn 400 - 680 tiến trình).
- **Hậu quả**: Làm cạn kiệt RAM, CPU và gây nghẽn nghiêm trọng cho hệ thống. Khi số lượng tiến trình Chromium mồ côi quá lớn, các lệnh duyệt tiến trình như `psutil.process_iter()` hoặc WMI query mất từ 20s - 80s+ cho mỗi lượt gọi, làm các script và closeout gate pytest bị timeout (300s).

### 3 Điểm yếu chết người của cơ chế dọn dẹp cũ:
1. **Chỉ gọi 1 endpoint `/profiles/stop/{id}`**: Khi profile mở nhiều tab hoặc browser bị treo, endpoint này thường trả về lỗi hoặc timeout nhưng script bỏ qua trong khối `except Exception: pass`, khiến browser tiếp tục chạy nền.
2. **Chỉ kill process theo debugging port (`--remote-debugging-port`)**: Khi port đã đóng hoặc browser mẹ bị lỗi, các process con (GPU process, renderer, utility workers) vẫn tiếp tục sống sót nhưng **không còn giữ cờ `--remote-debugging-port`**, dẫn đến việc bộ lọc bỏ sót toàn bộ các tiến trình con này.
3. **Nguy cơ tắt nhầm Google Chrome cá nhân**: Nếu lọc không chặt chẽ theo đường dẫn binary GPMLogin, các lệnh kill process có thể vô tình tắt nhầm trình duyệt Chrome làm việc cá nhân của user (`C:\Program Files\Google\Chrome\Application\chrome.exe`).

---

## 2. Quy chuẩn Bulletproof Cleanup (Chuẩn Bất Biến)

Mọi module đóng profile GPM (`gpm_client.py`, pipeline runner, batch worker) bắt buộc phải tuân thủ chuẩn 2 bước:

### Bước 1: Fallback kép qua cả 2 endpoint GPM API
Gọi tuần tự `/profiles/close/{profile_id}` và `/profiles/stop/{profile_id}`:
```python
for endpoint in ["close", "stop"]:
    try:
        res = requests.get(f"{GPM_BASE}/profiles/{endpoint}/{profile_id}", timeout=10)
        if res.status_code == 200:
            break
    except Exception:
        pass
```

### Bước 2: Quét & Force-kill đa điều kiện kèm Guardrail Chrome cá nhân
Điều kiện match tiến trình bắt buộc phải thỏa mãn:
1. **Hard Guardrail**: `CommandLine` BẮT BUỘC chứa keyword `gpmlogin` (hoặc đường dẫn `*GPMLogin*`). Nếu không có keyword này -> **BỎ QUA NGAY LẬP TỨC**.
2. **Target Matching**: So khớp linh hoạt theo 1 trong 3 tiêu chí:
   - Remote debugging port (`--remote-debugging-port={port}`)
   - Profile user data directory (`--user-data-dir` khớp hoặc chứa đường dẫn profile)
   - Profile ID xuất hiện trong bất kỳ đối số command line nào (`clean_pid in arg.lower()`)

#### Triển khai mẫu bằng Python `psutil`:
```python
if psutil is not None:
    try:
        time.sleep(1.0)
        target_port_flag = rf"^--remote-debugging-port={remote_port}$" if (remote_port and 0 < remote_port <= 65535) else None
        norm_target_path = os.path.normpath(profile_path).lower() if profile_path else None
        clean_pid = profile_id.lower()

        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                p_name = (p.info.get('name') or '').lower()
                if 'chrome' in p_name:
                    cmdline = p.info.get('cmdline') or []
                    # BẢO VỆ CHROME CÁ NHÂN: Chỉ can thiệp tiến trình thuộc GPMLogin
                    if not any('gpmlogin' in arg.lower() for arg in cmdline):
                        continue

                    match = False
                    if target_port_flag and any(re.match(target_port_flag, arg) for arg in cmdline):
                        match = True
                    if not match and norm_target_path:
                        for arg in cmdline:
                            if arg.startswith("--user-data-dir="):
                                val = arg.split("=", 1)[1].replace('"', '').replace("'", "")
                                norm_val = os.path.normpath(val).lower()
                                if norm_val == norm_target_path or norm_target_path in norm_val:
                                    match = True
                                    break
                    if not match and any(clean_pid in arg.lower() for arg in cmdline):
                        match = True

                    if match:
                        p.terminate()
                        try:
                            p.wait(timeout=1.5)
                        except Exception:
                            p.kill()
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Lỗi dọn dẹp tiến trình Chrome profile {profile_id}: {e}")
```

#### Triển khai mẫu bằng PowerShell WMI (cho script runner):
```powershell
Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -like '*GPMLogin*') -and ($_.CommandLine -like "*$pid*" -or $_.CommandLine -match "$port") } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
```

---

## 3. Lệnh Cấp Cứu Dọn Dẹp Tiến Trình Mồ Côi Toàn Hệ Thống

Khi phát hiện hệ thống bị treo hoặc tích tụ Chromium sau khi batch bị dừng đột ngột:
```bash
powershell -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*GPMLogin\gpm_browser*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"
```
*Lưu ý an toàn*: Câu lệnh trên nhắm trực tiếp vào thư mục cài đặt `GPMLogin\gpm_browser`, đảm bảo 100% không ảnh hưởng đến Chrome cá nhân đang mở tabs công việc của người dùng.

---

## 4. Yêu Cầu Unit Test Khi Chốt Phiên (Sol Auditor Reviewer Checklist)

Khi sửa đổi logic dọn dẹp process, Sol Auditor Reviewer trong Closeout Gate yêu cầu test case chứng minh thực tế:
1. **Test Personal Chrome Isolation**: Tạo mock process Chrome cá nhân và mock process GPM, assert `p_personal.terminate.assert_not_called()` và `p_gpm.terminate.assert_called_once()`.
2. **Test Multi-Endpoint Fallback**: Mock endpoint `/close` fail (HTTP 500) và `/stop` thành công (HTTP 200), assert gọi đủ 2 lần endpoint và trả về status thành công.
