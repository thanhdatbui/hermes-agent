# Bẫy Stale Quota History của Claude CLI & Quy chuẩn Cấu hình Antigravity Pro Pool

## 1. Bẫy Stale Quota History trong Claude Worker Dispatch

Trong hệ thống điều phối `dispatch_worker.py` và `claude_worker.py`:
- `claude_worker.py` đọc trạng thái hạn mức từ file lịch sử của Claude Code CLI:
  `%APPDATA%/Claude/plan-usage-history.json`
- Script kiểm tra độ tươi của dữ liệu với hằng số:
  `MAX_QUOTA_STALE_HOURS = 2.0` (tối đa 2 giờ).
- Nếu `t_now - t_sample > 2 * 3600`, hàm `get_claude_quota_status()` lập tức đánh dấu `is_stale: True`.

### Hiện tượng Báo Ảo Quota:
Khi hệ thống chạy các ca nuôi farm hoặc không gọi Claude CLI trong hơn 2 giờ:
1. `plan-usage-history.json` không được Claude CLI cập nhật mẫu mới.
2. `claude_worker.py` kích hoạt Quota Gate và từ chối thực thi với thông báo:
   `{"event": "quota_gate_triggered", "reason": "stale_quota", "fh": 5.0, "sd": 0.0, "role": "worker"}`
3. `dispatch_worker.py` ngộ nhận rằng tài khoản Claude đã cạn kiệt quota và ép fallback sang Antigravity CLI.
4. **Sự thật thực tế:** Tài khoản Claude Pro hoàn toàn khỏe mạnh, hạn mức 5h mới dùng 8% (trần 85%), hạn mức tuần 12% (trần 90%).

### Giải pháp Kỹ thuật Triệt để:
1. **Script Làm tươi Dữ liệu:** `python D:/Taadaa/tools/refresh_claude_quota_file.py` cập nhật mẫu dữ liệu mới với timestamp hiện tại.
2. **Cronjob Tự động Canh giữ:** Tạo cronjob `refresh-claude-quota-watchdog` chạy mỗi 30 phút (`*/30 * * * *`) để giữ file lịch sử luôn tươi mới (<30 phút), triệt tiêu hoàn toàn lỗi stale quota.

---

## 2. Quy chuẩn Ánh xạ Antigravity Pro Pool 1-1 với GPMLogin

Khi cấu hình dàn Worker Antigravity CLI (`ag_cli.py`) tại `D:/Taadaa/agy_profiles/`:

### A. Ba Tiêu Chuẩn Bắt Buộc (Invariant Triệt Để):
1. **Chỉ nhận Tài khoản Pro (`g1-pro-tier` / Google AI Pro):**
   - Phải kiểm tra trường `provider_specific_data` trong database OmniRoute (`C:/Users/Kibe/.omniroute/storage.sqlite`).
   - Tuyệt đối không nạp tài khoản `free-tier` vào pool worker.
2. **Sandbox Độc Lập Hoàn Toàn (Chống Dính Vân Tay Thiết Bị):**
   - Mỗi profile phải có UUID `installation_id` riêng biệt.
   - Bắt buộc tạo đầy đủ cấu trúc thư mục Windows ảo: `AppData/Roaming`, `AppData/Local`, `Temp` để `ag_cli.py` trỏ các biến môi trường `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP` vào đó, chống rò rỉ cache và Named Pipe.
3. **Ánh xạ Proxy 1-1 Chuẩn với Profile GPM:**
   - TUYỆT ĐỐI CẤM gán proxy tuần tự ngẫu nhiên (`acc_01 -> mobi1`, `acc_02 -> mobi2`...).
   - Bắt buộc truy vấn GPM API (`:19995/api/v3/profiles`) để lấy chính xác trường `raw_proxy` mà tài khoản đó đang dùng trong trình duyệt GPM.
   - Tài khoản đăng nhập ở IP nào thì gọi API bằng đúng IP đó để tránh bị Google kích hoạt cơ chế chống gian lận `VALIDATION_REQUIRED` (403).

### B. Quy mô Dàn Pháo Thủ 22 Profiles Pro:
Hệ thống hiện tại duy trì 22 profiles Pro (`acc_01` đến `acc_22`) được giải nén qua `unpack_omni_connection.py`, ánh xạ chính xác proxy 4G Mobi/Khoalee tương ứng và xoay tua theo thuật toán Least-Recently-Used (LRU) kèm Atomic Exclusive Lock (`os.O_CREAT | os.O_EXCL`).
