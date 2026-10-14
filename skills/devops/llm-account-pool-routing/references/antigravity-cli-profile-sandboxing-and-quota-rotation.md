# Antigravity CLI Profile Sandboxing, Hardware ID Isolation & Quota Rotation

## Bối cảnh & Căn nguyên Kỹ thuật

Khi mở rộng quy mô chạy nhiều tài khoản Google One / Antigravity Pro trên Antigravity CLI (`agy`), có 2 cái bẫy kỹ thuật chết người nếu cấu hình ngây thơ:

1. **Dùng chung `installation_id` (Cực kỳ nguy hiểm):**
   - Mặc định, `agy.exe` đọc cấu hình từ thư mục `$USERPROFILE/.gemini/`.
   - File `.gemini/installation_id` chứa một chuỗi UUID duy nhất đại diện cho phần cứng máy tính.
   - Nếu xoay 20 tài khoản bằng cách đổi token hoặc đổi proxy mà vẫn trỏ chung vào một thư mục `.gemini/`, Google sẽ thấy: **Cùng 1 máy vật lý (chung `installation_id`) nhưng lại phát request từ 20 IP khác nhau trên khắp thế giới trong cùng một ngày** -> Dấu hiệu gian lận Sybil rõ ràng, dẫn đến nguy cơ bị khóa hàng loạt tài khoản Pro.

2. **So sánh Độ Sạch: Native `agy` CLI vs OmniRoute (`:20129`):**
   - **OmniRoute:** Giả lập L7 (thứ tự Header HTTP và JSON body fields qua `cliFingerprints.ts`), nhưng ở tầng L4/L5 transport lại dùng Node.js `undici/fetch`. Chữ ký bắt tay TLS (JA3/JA4) và HTTP/2 SETTINGS frames mang đặc trưng của Web Server/Node.js, có thể bị Google Cloud Armor/Envoy phát hiện khi quét bot.
   - **Native `agy.exe`:** Do chính Google compile (Go + BoringSSL). Chữ ký TLS, HTTP/2 framing, và token refresh logic là 100% "chính chủ", hoàn toàn không thể phân biệt với lập trình viên thật.

---

## Kiến trúc Sandbox Cô Lập (Profile Sandbox Architecture)

Để vận hành an toàn dàn tài khoản Pro, bắt buộc phải cô lập cả **Mã máy (`installation_id`)** lẫn **IP phát mạng (`Proxy`)** cho từng tài khoản:

```text
D:/Taadaa/agy_profiles/
  ├── profiles_config.json      # Quản lý danh sách profiles, path, proxy gán riêng
  ├── pool_state.json           # Lưu timestamp cooldown khi tài khoản chạm rate limit
  ├── acc_01/
  │     └── .gemini/
  │           ├── installation_id   # UUID4 riêng biệt của Acc 01
  │           ├── oauth_creds.json  # Token OAuth riêng của Acc 01
  │           └── google_accounts.json
  ├── acc_02/
  │     └── .gemini/
  │           ├── installation_id   # UUID4 riêng biệt của Acc 02
  │           ├── oauth_creds.json
  │           └── google_accounts.json
```

---

## Cơ chế Vận hành qua Controller `ag_cli.py`

Cầu nối `D:/Taadaa/tools/ag_cli.py` đóng vai trò Bộ điều phối Failover tự động (Headless Load Balancer):

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

### 4. Thuật toán Auto-Failover khi Chạm Quota (429):
1. **Lọc Candidate:** Duyệt danh sách profile được bật (`enabled: true`), sắp xếp theo thời gian cooldown tăng dần. Ưu tiên các profile `READY` (cooldown <= now).
2. **Inject Môi trường Độc Lập:**
   ```python
   env["USERPROFILE"] = profile_path     # Đảm bảo agy đọc .gemini riêng có installation_id riêng
   if profile_proxy:
       env["HTTPS_PROXY"] = profile_proxy
       env["HTTP_PROXY"] = profile_proxy
   ```
3. **Bắt Lỗi Quota:** Kiểm tra stdout/stderr bắt các dấu hiệu: `resource_exhausted`, `429`, `quota exceeded`, `rate limit`, `out of quota`.
4. **Kích hoạt Cooldown & Chuyển Nick:**
   - Nếu dính lỗi quota: Gán cooldown 1800s (30 phút) vào `pool_state.json`.
   - In cảnh báo và tự động retry ngay với profile tiếp theo trong pool.
   - Nếu chạy thành công: Trả kết quả về cho Hermes Coordinator nghiệm thu.
