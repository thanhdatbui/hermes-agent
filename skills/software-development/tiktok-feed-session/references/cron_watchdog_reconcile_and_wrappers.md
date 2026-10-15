# Kiến trúc Cron Watchdog & Reconcile Window Buffer

## 1. Cơ chế Standalone Wrapper cho Cronjob Hermes
Hermes cron runner thực thi scripts từ thư mục isolated cache `~/.hermes/scripts/`. Khi script gốc trong repo (`scripts/feed_session_watchdog.py`) được module hóa thành package nội bộ (`scripts/watchdog/`), việc copy file đơn lẻ sẽ gây crash `ModuleNotFoundError` do thiếu dependency folder.

### Giải pháp kỹ thuật chuẩn hóa
- Thư mục `scripts/hermes_cron/` duy trì các file tự chứa (self-contained wrappers), nhúng trực tiếp process locks hoặc copy helper functions mà không phụ thuộc package ngoài.
- File kiểm thử `test_reconcile_helpers_in_sync_with_hermes_cron` trong pytest suite đảm bảo tính đồng bộ 100% (DRY parity) giữa `scripts/feed_session_watchdog.py` và `scripts/hermes_cron/feed_session_watchdog.py`.

## 2. Reconcile Window Buffer & Fail-Safe Default
Khi đối soát Following giữa SQLite snapshots và TikTok Web:
- **Phiên 1:** Giữ nguyên baseline `session_start_iso` để không nhảy vọt về tương lai.
- **Phiên 2 trở đi:** Mở rộng `session_start_iso` thêm +10 phút (`buffer_reconcile_iso`) để bắt kịp snapshot chốt ca ghi trễ của phiên trước.
- **Fail-Safe Default:** Mọi `session_key` không xác định rõ (None, empty, unknown format) phải mặc định coi như Phiên 1 (không buffer start) để bảo toàn baseline an toàn.
- **Guard đảo ngược:** Kiểm tra datetime sau khi buffer, tuyệt đối không để `query_start_iso >= session_end_iso`.

## 3. Cắt gọt và Subsecond Capping Boundary
- Khi buffer tiến về cuối ngày, `end_of_day` phải được chuẩn hóa với `microsecond=0` (`23:59:59`) thay vì `microsecond=999999` để đồng nhất với format lưu trữ SQLite và tránh lỗi so sánh subsecond khiến giá trị bị lọt qua không được clamp.
- Đối với trường hợp lùi thời gian (negative minutes), clamp chặn dưới tại `start_of_day` (`00:00:00`).
