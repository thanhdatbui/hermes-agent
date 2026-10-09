# Watchdog Feed Session & Tránh Chốt Sớm

## Đồng bộ 2 file Watchdog
Mọi sửa đổi logic trên `feed_session_watchdog.py` phải được áp dụng song song vào cả hai vị trí:
1. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
2. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`

## Runner Patterns mở rộng
Hàm `is_feed_runner_active()` phải giám sát đầy đủ các patterns của process runner/uploader để tránh sót việc background còn đang chạy:
- `multi_machine_feed_session`
- `multi-machine-feed-session`
- `run-feed-session.ps1`
- `run_follow`
- `run_tiktok.py`
- `hermes_cron_runner.py`
- `tiktok_runner.py`
- `run_post.py`
- `tiktok_workflow`
- `tiktok_upload`

## Nguyên tắc chặn chốt sớm (`can_report_session`)
- Nếu `is_today and runner_busy`: hàm `can_report_session()` **phải trả về `False` ngay từ đầu**.
- Tuyệt đối không để nhánh kiểm tra `completed_expected_count >= expected_count` chốt trước khi kiểm tra `runner_busy` trong ngày hôm nay, tránh việc uploader / workflow còn đang xử lý dở dang mà watchdog đã gửi Telegram kết thúc phiên.

## Quy trình Reset Báo Cáo Phiên
Khi một phiên bị chốt nhầm và cần watchdog tính toán, gửi báo cáo lại:
1. Mở file `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json`.
2. Xóa session identifier (ví dụ `"2026-09-19_ca1_phien1"`) khỏi mảng `reported_sessions`.
3. Lưu file với định dạng JSON chuẩn.
