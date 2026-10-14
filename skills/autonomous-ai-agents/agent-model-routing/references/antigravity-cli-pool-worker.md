# Antigravity CLI Pool Worker (`ag_cli.py` & `agy.exe`)

## 1. Kiến trúc phân vai (Coordinator vs Worker)

- **Coordinator (Hermes Agent):**
  - Giữ vai trò trực ban 24/7, nghe alert Farm, điều khiển Telegram, OCR vision, ADB devices.
  - Sử dụng pool model qua OmniRoute (`localhost:20129`) với **Sticky Session** (`stickyRoundRobinLimit: 15`) để tận dụng Prompt Caching của Google Gemini (tiết kiệm token context dài 30k-100k).
- **Worker (Thợ code chuyên trách):**
  - Toàn bộ task sửa code, refactor, phân tích file nặng được bàn giao cho `D:/Taadaa/tools/ag_cli.py`.
  - Binary thực thi là `agy.exe` (Go runtime, BoringSSL TLS fingerprint thật 100%).
  - Chạy theo cơ chế **Stateless / One-shot**: 5-25s đọc AST, sửa diff và tự kích hoạt terminal nội bộ chạy test trước khi trả kết quả.

## 2. Quản lý Pool Profile Sandbox (`D:/Taadaa/agy_profiles/`)

- **Cấu hình:** `profiles_config.json` quản lý danh sách `acc_01`, `acc_02`, ... `acc_21`.
- **Cô lập môi trường Layer 7 & OS:**
  - `installation_id`: UUID độc lập riêng biệt cho mỗi profile (không chung UUID máy).
  - Thư mục riêng: `USERPROFILE`, `HOME`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP` trỏ vào profile dir tương ứng.
  - Proxy 4G gắn chết theo từng nick (`HTTPS_PROXY=http://user:pass@host:port`), đồng bộ 1:1 từ GPM.

## 3. Cơ chế Điều phối Tải (Load Balancing & Safety Locks)

- **Khóa nguyên tử đa tiến trình (Atomic Concurrency Lease):**
  - Dùng `os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)` cấp hệ điều hành chống race condition.
  - Fail-Closed: nếu lock file bị corrupt hoặc lỗi đọc, coi như profile đang bận để chuyển nick khác.
  - Dead PID Detection (`psutil.pid_exists(pid)`) tự gỡ khóa ngay khi tiến trình crash, không đợi hết timeout 300s.
- **Thuật toán điều phối Least-Recently-Used (LRU):**
  - Khi có task mới, sắp xếp danh sách sẵn sàng theo `last_used` tăng dần (ưu tiên nick nghỉ lâu nhất).
  - Tránh dồn tải nặng vào 1 nick gây nghẽn RPM/TPM của Google.
- **Failover & Exponential Backoff Cooldown:**
  - Phát hiện `429`, `RESOURCE_EXHAUSTED`, `quota exceeded`.
  - Phạt cooldown lũy tiến: lần 1 = 30 phút, lần 2 = 60 phút, lần 3 = 120 phút.
  - Jitter ngẫu nhiên 5-10s trước khi chuyển nick tiếp theo để chống Google burst correlation.

## 4. Lệnh thực thi mẫu cho Coordinator

```bash
# Sửa code / thực thi task
python D:/Taadaa/tools/ag_cli.py fix "Mô tả task cần sửa..." --file "đường_dẫn_file"

# Kiểm tra trạng thái pool
python D:/Taadaa/tools/ag_cli.py pool-status

# Hỏi đáp / phân tích context qua profile cụ thể
python D:/Taadaa/tools/ag_cli.py ask "Câu hỏi phân tích" --profile acc_02
```
