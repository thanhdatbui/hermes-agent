# Tránh Tranh Chấp Máy Giữa Các Repo & Chặn Treo Do Grep Recursive Toàn Root

## 1. Tranh Chấp Thiết Bị (Device Lock Collision: Hotmail/Reg vs Cron Nuôi Acc)

### Triệu chứng
- Khi chạy flow thủ công / batch (ví dụ Hotmail login, Add mail khôi phục, TikTok Reg), cron nuôi acc (`run_tiktok.py` / `multi-machine-feed-session`) vẫn tự động bốc máy đó vào ca lướt.
- Hậu quả: TikTok mở đè lên app Outlook / Gmail đang thao tác -> Cron nuôi acc phát hiện mất focus TikTok (`com.ss.android.ugc.trill focus lost`) và kích hoạt `preserve_blocker_screen`, gửi cảnh báo dừng phiên lên Farm Alerts.

### Nguyên nhân gốc
- Runner của flow thủ công không tạo file lock hoặc tạo lock với `user_authorized=False` (no-op lease) nên không ghi file lock `machine_<STT>.lock.json` vào thư mục `C:\Users\Kibe\.codex\device-locks\`.
- Cron nuôi acc khi kiểm tra `acquire_device_lock` không thấy lock file của máy nên coi là máy rảnh và khởi chạy bình thường.

### Quy tắc khắc phục bắt buộc
1. **Tạo Lock Đích Danh Khi Chạy Tác Vụ Thủ Công / Batch Ngoại Lệ**:
   - Khi chạy script thủ công (Hotmail, Gmail, TikTok Reg) ngoài lịch cron: Phải kích hoạt device lock với `user_authorized=True` và `status="running"` để ghi `machine_<STT>.lock.json` và `serial_<SERIAL>.lock.json`.
2. **Cron Nuôi Acc Skip An Toàn Khi Thấy Lock**:
   - `run_tiktok.py` và `multi_machine_feed_session.py` tự động bắt ngoại lệ `DeviceLockUnavailable` -> log `[device-lock] machine <M> is locked by ...` và skip máy an toàn, không cố mở app đè lên.

---

## 2. Phòng Tránh Grep / Search Đệ Quy Vô Hạn Trên Root `D:\Taadaa`

### Triệu chứng
- Tiến trình `grep.exe -rn ... /d/Taadaa` chạy ngầm ngốn tài nguyên, CPU/Disk bận kéo dài >20-30 phút mà không kết thúc.
- Bot Hermes trong các channel Telegram hiển thị trạng thái `Working — 24 min — iteration ...` và bị chặn phản hồi câu hỏi của user.

### Nguyên nhân
- Root `D:\Taadaa` chứa 15+ repository con kèm theo các thư mục khổng lồ: `.git/`, `.venv/`, `python-envs/`, `node_modules/`, `runtime/` (chứa hàng chục GB screenshots PNG, UI XML dumps, video renders, logs).
- Chạy `grep -rn` không giới hạn đường dẫn quét qua hàng triệu file nhị phân và text khổng lồ.

### Quy tắc khắc phục
1. **CẤM TUYỆT ĐỐI grep đệ quy trên root `D:\Taadaa`**:
   - Chỉ tìm kiếm trong thư mục đích danh (ví dụ `D:\Taadaa\tiktok-luot nuoi acc\python_runner` hoặc `D:\Taadaa\Hotmail`).
2. **Loại trừ các thư mục rác / binary / runtime**:
   - Luôn thêm `--exclude-dir={.git,.venv,venv*,runtime,artifacts,node_modules,BACKUP_ALL}` nếu buộc phải grep trên phạm vi rộng.
3. **Ưu tiên dùng công cụ có sẵn `search_files`** (ripgrep-backed) thay vì gọi `grep.exe` qua terminal.
