# TikTok Farm Account Tracking & Workbook Delta Protocol (2026-09-17)

## 1. Nguồn dữ liệu
- Nguồn danh sách tài khoản hợp lệ: `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (Cột `May`, `Device ID`, `ID`, `Video Đã Đăng`).
- Đọc bỏ qua các ô `None` hoặc rỗng; lấy toàn bộ ~590 nick đang hoạt động của farm.

## 2. Quét số liệu không phụ thuộc thiết bị
- Script: `D:/Taadaa/tools/tiktok_account_tracker.py`.
- Sử dụng mobile Safari headers để bóc tách JSON hydration từ `https://www.tiktok.com/@{username}`:
  - `followerCount`, `heartCount`, `videoCount`, `followingCount`.
  - UID (`user.id`) và SecUID (`user.secUid`).
  - Trạng thái nick: `LIVE` hoặc `DIE / NOT_FOUND` (HTTP 404 / `statusCode == 10221`).

## 3. Theo dõi tăng trưởng & Cắn đề xuất
- Lưu trữ time-series: `D:/Taadaa/data/tiktok_tracker.db`.
- Tự động đối chiếu $\Delta$ Follower và $\Delta$ Like giữa các mốc thời gian:
  - Gắn cờ `🔥 CẮN ĐỀ XUẤT` khi follower tăng $\ge 10$ hoặc like tăng $\ge 50$.
- Xuất báo cáo Excel hàng ngày: `D:/OneDrive/TaadaaData/kibe/tiktok_stats_farm.xlsx`.

## 4. Tự động hóa Cron 07:00
- Cron job `daily-tiktok-farm-tracker` (`0 7 * * *`) chạy wrapper `cron_tiktok_daily_tracker.py` được đồng bộ tại 3 nơi:
  1. `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_tiktok_daily_tracker.py`
  2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_tiktok_daily_tracker.py`
  3. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/cron_tiktok_daily_tracker.py`
- Tự động đẩy báo cáo tóm tắt về Telegram khung 07:00 sáng.
