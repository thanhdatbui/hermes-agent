# Device Locks Watchdog & Auto-Reap Synchronization

## Triệu chứng
- Telegram Watchdog báo danh sách máy `⚠️ (QUÁ HẠN > 2H)` dù hệ thống có cronjob dọn lock định kỳ.
- Người vận hành hoang mang vì tưởng cơ chế auto-unlock bị hỏng.

## Nguyên nhân (Cron Phase Race)
- Cron dọn lock (`reap-dead-owner-locks.py`) chạy ở mốc cố định: `0, 15, 30, 45`.
- Cron cảnh báo (`watch_device_locks.py`) chạy lệch pha (ví dụ mốc `56`), quét thấy lock vừa vượt qua 120 phút (ví dụ 124, 128 phút) trước khi tick reaper tiếp theo (mốc `00`) kịp chạy.

## Quy chuẩn đồng bộ (Synchronization Standard)
1. **Preflight Auto-Reap trong Watchdog:**
   - Trong `watch_device_locks.py`, trước khi quét danh sách lock để lập báo cáo, BẮT BUỘC tự động gọi chạy `reap-dead-owner-locks.py` (preflight execution) để dọn sạch toàn bộ lock hết hạn TTL (> 2h) hoặc dead-owner trước.
2. **Lệch pha chủ động theo lịch:**
   - Đặt lịch cron của Watchdog chạy ngay sau mốc reaper 1 phút (ví dụ: `1, 16, 31, 46 * * * *`).
3. **Đồng bộ đa vị trí script:**
   - Khi chỉnh sửa `watch_device_locks.py`, phải đồng bộ trên cả 3 đường dẫn:
     - `~/AppData/Local/hermes/scripts/watch_device_locks.py`
     - `~/.hermes/scripts/watch_device_locks.py`
     - `D:/Taadaa/Hermes/deploy/hermes-home/scripts/watch_device_locks.py` / `D:/Taadaa/tools/watch_device_locks.py`
