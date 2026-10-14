# Antigravity CLI Profile Sandboxing, Hardware ID Isolation & Quota Rotation

## Bối cảnh & Căn nguyên Kỹ thuật

Khi mở rộng quy mô chạy nhiều tài khoản Google One / Antigravity Pro trên Antigravity CLI (`agy`), có các cái bẫy kỹ thuật chết người nếu cấu hình ngây thơ:

1. **Dùng chung `installation_id` (Cực kỳ nguy hiểm):**
   - Mặc định, `agy.exe` đọc cấu hình từ thư mục `$USERPROFILE/.gemini/`.
   - File `.gemini/installation_id` chứa một chuỗi UUID duy nhất đại diện cho phần cứng máy tính.
   - Nếu xoay 20 tài khoản bằng cách đổi token hoặc đổi proxy mà vẫn trỏ chung vào một thư mục `.gemini/`, Google sẽ thấy: **Cùng 1 máy vật lý (chung `installation_id`) nhưng lại phát request từ 20 IP khác nhau trên khắp thế giới trong cùng một ngày** -> Dấu hiệu gian lận Sybil rõ ràng, dẫn đến nguy cơ bị khóa hàng loạt tài khoản Pro.

2. **So sánh Độ Sạch: Native `agy` CLI vs OmniRoute (`:20129`):**
   - **OmniRoute:** Giả lập L7 (thứ tự Header HTTP và JSON body fields qua `cliFingerprints.ts`), nhưng ở tầng L4/L5 transport lại dùng Node.js `undici/fetch`. Chữ ký bắt tay TLS (JA3/JA4) và HTTP/2 SETTINGS frames mang đặc trưng của Web Server/Node.js, có thể bị Google Cloud Armor/Envoy phát hiện khi quét bot và dẫn tới nguy cơ quét chết chùm 20 tài khoản.
   - **Native `agy.exe`:** Do chính Google compile (Go + BoringSSL). Chữ ký TLS, HTTP/2 framing, và token refresh logic là 100% "chính chủ", hoàn toàn không thể phân biệt với lập trình viên thật.

3. **Bẫy Rò rỉ Cache Windows (`APPDATA` / `LOCALAPPDATA` / `TEMP`):**
   - Nếu chỉ đổi `USERPROFILE`, binary `agy.exe` và Chromium/Google engine vẫn đọc/ghi cache và lock vào `C:\Users\<user>\AppData\Local\...`.
   - Khi đó, cả 20 profiles dùng chung local cache, Google soi tầng device cache sẽ phát hiện chạy chung máy. Bắt buộc phải cô lập toàn bộ các biến môi trường hệ thống.

---

## Kiến trúc Sandbox Cô Lập Đầy Đủ (Full Sandbox Architecture)

Mỗi tài khoản được cấp một sandbox trọn vẹn tại `D:/Taadaa/agy_profiles/<name>/`:

```text
D:/Taadaa/agy_profiles/
  ├── profiles_config.json      # Quản lý danh sách profiles, path, proxy gán riêng
  ├── pool_state.json           # Lưu timestamp cooldown khi tài khoản chạm rate limit
  ├── acc_01/
  │     ├── .profile.lock       # File lock chiếm dụng profile (tránh race condition)
  │     ├── AppData/
  │     │     ├── Roaming/      # Cô lập %APPDATA%
  │     │     └── Local/        # Cô lập %LOCALAPPDATA% (chống leak cache)
  │     ├── Temp/               # Cô lập %TEMP% và %TMP%
  │     └── .gemini/
  │           ├── installation_id   # UUID4 riêng biệt của Acc 01
  │           ├── oauth_creds.json  # Token OAuth riêng của Acc 01
  │           └── google_accounts.json
```

---

## Cơ chế Vận hành & Bảo vệ qua Controller `ag_cli.py`

Cầu nối `D:/Taadaa/tools/ag_cli.py` đóng vai trò Bộ điều phối Failover tự động (Headless Load Balancer & Safety Controller):

### 1. Khởi tạo Profile Sandbox Mới:
```bash
# Tạo acc_02 gắn với Proxy di động 4G (cổng 20002)
python D:/Taadaa/tools/ag_cli.py init-profile acc_02 --proxy "http://127.0.0.1:20002"

# Hoặc khởi tạo acc_01 bằng cách sao chép credentials hiện tại trên máy
python D:/Taadaa/tools/ag_cli.py init-profile acc_01 --copy-current
```

### 2. Đăng nhập tài khoản Google cho Sandbox:
```bash
# Set USERPROFILE trỏ vào đúng sandbox rồi chạy agy login
USERPROFILE="D:/Taadaa/agy_profiles/acc_02" agy login
```

### 3. Kiểm tra trạng thái Pool:
```bash
python D:/Taadaa/tools/ag_cli.py pool-status
```
Báo cáo: Tên profile, Proxy gán kèm, Trạng thái (`READY` / `COOLDOWN`), và thời gian còn lại trước khi hồi quota.

### 4. Bốn Chốt Chặn P0 Đã Tích Hợp (Sol Web Audit Certified):

1. **Full Environment Injection:**
   ```python
   env["USERPROFILE"] = prof_dir
   env["HOME"] = prof_dir
   env["APPDATA"] = os.path.join(prof_dir, "AppData", "Roaming")
   env["LOCALAPPDATA"] = os.path.join(prof_dir, "AppData", "Local")
   env["TEMP"] = os.path.join(prof_dir, "Temp")
   env["TMP"] = os.path.join(prof_dir, "Temp")
   if prof_proxy:
       env["HTTPS_PROXY"] = prof_proxy
       env["HTTP_PROXY"] = prof_proxy
   ```

2. **Profile Lease Locking (`.profile.lock`):**
   - Chống race condition khi nhiều cronjob hoặc subagent gọi `ag_cli.py` cùng một thời điểm.
   - Ghi JSON `{"pid": ..., "timestamp": ...}` với lease timeout 300s.
   - **Tự dọn Stale Lock (Dead PID Check):** Dùng `psutil.pid_exists(pid)`. Nếu tiến trình trước đã chết do crash/timeout, lock được giải phóng ngay lập tức, không làm kẹt profile 300s.

3. **Failover Jitter (Chống cụm hành vi Bot):**
   - Khi dính lỗi quota (`RESOURCE_EXHAUSTED`, `429`, `quota exceeded`), script ghi nhận cooldown 1800s vào `pool_state.json`.
   - Trước khi thử lại với profile kế tiếp, tự động `time.sleep(random.uniform(5.0, 10.0))` để tránh tạo ra mẫu burst correlation gửi request liên tiếp từ nhiều nick.

4. **Kỷ luật Timeout khi Gọi Lệnh `fix`:**
   - Lệnh `ag_cli.py ask` trả lời rất nhanh (2-5s), chạy foreground an toàn.
   - Lệnh `ag_cli.py fix` trên các file lớn cần thời gian suy luận và chỉnh sửa AST từ 70-90s, vượt quá trần foreground timeout 60s của harness Coordinator/Worker.
   - **Quy tắc bắt buộc:** Khi gọi `ag_cli.py fix`, bắt buộc chạy qua `terminal(background=True, notify_on_complete=True, timeout=120)` để tránh bị kill nhầm giữa chừng.
