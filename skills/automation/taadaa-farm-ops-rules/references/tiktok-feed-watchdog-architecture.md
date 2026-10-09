# TikTok Feed Watchdog Architecture & Hermes Cron Safety

## 1. Watchdog chính thức duy nhất
- **Tên Cron:** `tiktok-feed-session-watchdog` (Job script: `feed_session_watchdog.py`)
- **Cơ chế:** Đọc trực tiếp tiến trình và artifact thực tế tại `D:/Taadaa/runtime/kibe/live/<date>/row-*`.
- **Nguyên tắc báo cáo:** Chỉ báo cáo 1 lần khi phiên hoàn tất (đủ số máy dự kiến theo row hoặc hết giờ phiên và runner đã dừng). Không báo cáo cắt ngọn thiếu máy.

## 2. Loại bỏ hoàn toàn Legacy Manifest Watcher (`phase9-watcher-tiktok-feed`)
- **Nguyên nhân cấm:** `tiktok_watcher.py` gọi `hermes_cron_watcher.py` và yêu cầu `load_active(..., expected_source=source)` phải khớp tuyệt đối SHA revision giữa file manifest sinh từ đầu ngày với file nguồn `hermes_cron_source_config.json` / `taikhoan_run_safe.xlsx`.
- **Hiện tượng lỗi:** Khi `taikhoan_sync_cron` đồng bộ lại Excel trong ngày (thay đổi nick, cập nhật video count), `hermes_cron_source_config.json` đổi revision -> `hermes_cron_watcher.py` văng lỗi `ValueError: MANIFEST_IDENTITY_MISMATCH` và gửi thông báo lỗi sai lệch về Telegram.
- **Hành động chuẩn:** Không sử dụng `phase9-watcher-tiktok-feed`. Toàn bộ việc giám sát giao cho `feed_session_watchdog.py`.
