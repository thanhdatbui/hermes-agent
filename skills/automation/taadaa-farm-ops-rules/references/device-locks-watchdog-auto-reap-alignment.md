# Device Locks Watchdog Preflight & Auto-Reap Alignment

## Vấn đề lệch pha (Cron Phase Misalignment)
- Script dọn dẹp `reap-dead-owner-locks.py` chạy ở các phút `00, 15, 30, 45`.
- Script giám sát `watch_device_locks.py` quét danh sách lock theo chu kỳ riêng (ví dụ phút `56`).
- Nếu một lock đạt tuổi 124 phút ở phút 56, nó vượt ngưỡng 120 phút (2h TTL) nhưng chưa đến mốc dọn dẹp tiếp theo (phút 00), dẫn đến Watchdog gửi thông báo cảnh báo `QUÁ HẠN > 2H` trên Telegram, gây hiểu nhầm là hệ thống không tự mở khóa.

## Giải pháp chuẩn hóa (Standard Pattern)
1. **Preflight Auto-Reap & Advisory Mutex (`.reaper.lock`):**
   - Khi `reap-dead-owner-locks.py` chạy, nó tạo file khóa tạm `~/.codex/device-locks/.reaper.lock`.
   - `watch_device_locks.py` kiểm tra file `.reaper.lock`. Nếu file tồn tại và mtime < 120s trước (Reaper đang quét dọn), Watchdog tự động bỏ qua lượt quét này (skip tick) để tránh đọc file đang đổi tên hoặc báo động giả.
2. **Cron Schedule Alignment:** Lịch chạy cron của watchdog được xếp sau reaper đúng 1 phút (`1, 16, 31, 46 * * * *`) để đảm bảo dữ liệu gửi về Telegram luôn là trạng thái đã được dọn sạch các lock hết hạn. Ngưỡng cảnh báo kẹt lock được tối ưu xuống **90 phút** (thay vì 120 phút) để cảnh báo sớm trong ca.
3. **Triple Path Sync:** File `watch_device_locks.py` luôn được đồng bộ nhất quán tại 3 vị trí:
   - `C:/Users/Kibe/AppData/Local/hermes/scripts/watch_device_locks.py` (Hermes live launcher)
   - `~/.hermes/scripts/watch_device_locks.py` (Fallback runner)
   - `D:/Taadaa/Hermes/deploy/hermes-home/scripts/watch_device_locks.py` (Source repo)
