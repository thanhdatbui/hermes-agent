# Taadaa Farm Cron Safe Source Sync & Row 5-6 Scheduling

## 1. Single Source of Truth: `taikhoan_run_safe.xlsx`
- Bắt buộc đọc trực tiếp từ `taikhoan_run_safe.xlsx` (480 rows = 80 máy x 6 rows).
- CẤM tự tạo workbook phụ hoặc lọc thiếu dải máy 1..80.
- `hermes_taikhoan_sync_cron.py` tự động đồng bộ `hermes_cron_source_config.json`, `feed_state.json`, `post_state.json` và tái tạo manifest active trong ngày để tránh lỗi `MANIFEST_IDENTITY_MISMATCH`.

## 2. Schedule Parity & Warmup Policy
- Lịch phân bổ:
  + Ngày Lẻ (1, 3, 5): Ca 1 (Row 1), Ca 2 (Row 3), Ca 3 (Row 5).
  + Ngày Chẵn (2, 4, 6): Ca 1 (Row 2), Ca 2 (Row 4), Ca 3 (Row 6).
- Row 1, 2 chỉ nuôi ca sáng (Ca 1).
- Row 5, 6 (nick mới): 10 ngày đầu chỉ lướt feed -> 10 ngày tiếp theo đăng 5 video đầu -> ngày 21 mới mở follow.
