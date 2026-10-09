# Stale GPM Profile Watchdog & Cascade System Freeze Prevention

## 1. Bối cảnh & Cơ chế gây sập dây chuyền (Cascade Failure Anatomy)

Khi chạy các script batch hoặc one-off (như xác thực SĐT OpenAI 5sim, đăng nhập hàng loạt Gmail, cào dữ liệu):
- Script thường mở profile GPM liên tục trong vòng lặp bằng `GET /profiles/start/{id}`.
- Khi kết thúc phiên (thành công hoặc lỗi timeout, OTP từ chối, v.v.), nếu script chỉ gọi thô API:
  ```python
  requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
  ```
- **Hạn chế cố hữu của GPM Local API:**
  Endpoint `/profiles/stop/{id}` chỉ phát tín hiệu đóng mềm (WM_CLOSE). Khi Chromium bị kẹt bởi modal cảnh báo (*"Restore pages: GPM-Browser didn't shut down correctly"*), crash handler, hoặc renderer loop, GPM API **không thể kill tiến trình `chrome.exe`**.
- **Hậu quả tích tụ:**
  - Mỗi profile bỏ rơi 5–10 tiến trình con (`chrome.exe` GPU, Renderer, Utility, Crashpad).
  - Sau 20–30 lượt thử, Task Manager xuất hiện 50–100+ tiến trình Chrome mồ côi ngốn sạch RAM và CPU (100% tài nguyên máy).
  - **Sập OmniRoute (:20129):** Máy trạm cạn kiệt socket handle và CPU thread, khiến OmniRoute proxy không xử lý được request LLM, dội lỗi HTTP 429, 499, 504 và Semaphore timeout 30s.
  - **Tê liệt toàn bộ Watchdog định kỳ:** Các cronjob của Hermes (`hermes_stale_watchdog`, `post_evening_gpm_login_watchdog`...) khi đến giờ kích hoạt đều bị đơ do subprocess hoặc socket bị nghẽn I/O.

---

## 2. Kiến trúc giải pháp Watchdog quét profile treo > 1h (`gpm_stale_profile_watchdog.py`)

Để bảo vệ máy chủ khỏi nguy cơ spam profile mồ côi làm nghẽn hạ tầng, cần một watchdog chạy ngầm định kỳ (mỗi 10 phút, `no_agent=True`):

### A. Quy tắc đối soát bảo vệ Chrome cá nhân (Ironclad Guard)
CẤM TUYỆT ĐỐI kill nhầm trình duyệt của user hoặc các tiến trình farm khác:
1. `cmdline` chứa `google\chrome\user data` hoặc `google/chrome/user data` (không phân biệt hoa thường) ➔ **BỎ QUA NGAY** (Chrome cá nhân của User).
2. `cmdline` KHÔNG chứa chuỗi `gpmlogin` hoặc đường dẫn `programs\gpmlogin\profile` ➔ **BỎ QUA NGAY**.
3. CẤM can thiệp vào `xiaowei.exe`, ADB, Python, Hermes.

### B. Ngưỡng phát hiện treo (Stale Threshold)
- Tính thời gian sống của tiến trình: `age = time.time() - p.create_time()`.
- Ngưỡng chuẩn: `DEFAULT_STALE_THRESHOLD_SECONDS = 3600` (1 giờ).
- Nếu `age < 3600` ➔ Bỏ qua (cho phép các tác vụ nuôi tài khoản hoặc batch dài hạn đang chạy hợp lệ).
- Nếu `age >= 3600` ➔ Đưa vào danh sách cưỡng chế dọn dẹp.

### C. Quy trình dọn dẹp 2 pha (Graceful Stop + Force Kill Fallback)
1. **Trích xuất thông tin profile:**
   - Lấy `ProfilePath` từ cờ `--user-data-dir=...` (tên thư mục cuối cùng dưới `...\GPMLogin\profile\...`).
   - Truy vấn SQLite `profile_data.db`:
     ```sql
     SELECT Id, Name FROM profiles WHERE ProfilePath = ? OR Id = ?;
     ```
   - Xác định được `profile_id` và `profile_name` (email).
2. **Pha 1: Đồng bộ trạng thái GPM:**
   - Nếu GPM API (`:19995`) online: gọi `GET /profiles/stop/{profile_id}` để GPM cập nhật trạng thái UI/DB.
3. **Pha 2: Chấm dứt tiến trình cứng:**
   - Gọi `p.terminate()`, chờ tối đa 1.0–2.0s.
   - Nếu tiến trình chưa thoát: gọi `p.kill()`.
   - Quét và dọn sạch các tiến trình con: `p.children(recursive=True)` để không để sót renderer/GPU process.
4. **Telemetry & Audit Persistence:**
   - Phát metric ra `sys.stderr`:
     ```python
     sys.stderr.write(f"[TELEMETRY_METRIC] {json.dumps({'event': 'stale_gpm_reaped', 'pid': pid, 'profile_id': profile_id, 'profile_name': profile_name, 'age_seconds': int(age)}, ensure_ascii=False)}\n")
     ```
   - Đồng thời ghi bền vững vào file JSONL `Path.home() / "AppData" / "Local" / "hermes" / "logs" / "gpm_watchdog.jsonl"` với timestamp UTC ISO (`YYYY-MM-DDTHH:MM:SSZ`) để phục vụ audit/dashboard mà không bị mất dấu vết.
   - Bắt và xử lý an toàn mọi ngoại lệ hệ điều hành: `psutil.NoSuchProcess`, `psutil.AccessDenied`, `psutil.ZombieProcess` và `requests.RequestException` khi API đóng profile gặp trục trặc.

### D. Kỷ luật Silent Watchdog & Vận hành Production
- **BẮT BUỘC DELIVER: LOCAL (CHỐNG SPAM TELEGRAM):**
  + Các watchdog dọn dẹp tiến trình / rác hệ thống (janitor/reaper) hoạt động ở tần suất cao (mỗi 5–10 phút) **BẮT BUỘC gán `deliver: local`** (lưu log ra output file local, tuyệt đối KHÔNG cấu hình `deliver: origin` hoặc `telegram:...`).
  + Việc bắn thông báo dọn dẹp định kỳ vào Telegram gây loãng kênh điều hành và spam phiền toái cho User.
- **LỌC SUB-PROCESS & KHỬ TRÙNG LẶP CHROME (ANTI-PID-SPAM):**
  + Mỗi profile Chrome mở ra sẽ kéo theo 5–10 tiến trình con (`--type=renderer`, `--type=gpu-process`, `--type=utility`, `crashpad`).
  + Watchdog **BẮT BUỘC bỏ qua** các tiến trình con bằng cách kiểm tra:
    ```python
    if any(arg.startswith("--type=") for arg in cmdline):
        continue
    ```
  + Chỉ nhắm vào tiến trình Chrome gốc (browser process) và khử trùng lặp qua tập hợp `seen_profiles` (theo `profile_id` hoặc `profile_path`) để 1 profile chỉ xuất hiện đúng 1 dòng duy nhất khi dọn dẹp.
- **Triển khai Production & Cronjob:**
  - Script path: `deploy/hermes-home/scripts/gpm_stale_profile_watchdog.py` (đồng bộ `AppData/Local/hermes/scripts/`).
  - Lịch chạy: `cronjob` schedule `*/10 * * * *`, cờ `no_agent=True`, `deliver: local`.
  - Lệnh test kiểm thử:
    ```bash
    # Quét thử nghiệm không can thiệp tiến trình:
    python C:/Users/Kibe/AppData/Local/hermes/scripts/gpm_stale_profile_watchdog.py --dry-run
    ```

---

## 3. Quy chuẩn bắt buộc cho mọi Batch / One-off Script

Mọi script tự động mở profile GPM (kể cả script test nhanh, script nạp sim 5sim, script cào dữ liệu) **BẮT BUỘC** tuân thủ:
1. Không bao giờ chỉ gọi `requests.get('/profiles/stop/{id}')` trong `finally:`.
2. Bắt buộc import và dùng `GPMClient.stop_profile(profile_id, port)` từ `D:\Taadaa\GPM auto\src\gpm_client.py` (đã tích hợp sẵn psutil process reaper).
3. Hoặc nếu viết standalone script, phải mang theo helper hàm dọn dẹp tiến trình có đối soát `--user-data-dir` khớp với profile vừa chạy.
