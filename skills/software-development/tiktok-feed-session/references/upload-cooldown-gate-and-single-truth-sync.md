# Upload Cooldown Gate & Single-Truth Sync Rules

## 1. Single-Truth Sync Rule (`taikhoan_run_safe.xlsx`)
- `taikhoan_run_safe.xlsx` là **chân lý duy nhất (single source of truth)** cho toàn bộ hệ thống feed runner và upload/follow runners.
- Script cron `hermes_taikhoan_sync_cron.py` chạy định kỳ 5 phút CHỈ thực hiện đồng bộ 1 chiều:
  `taikhoan_dat_v2` + `Tik1..Tik6.xlsx` $\rightarrow$ `taikhoan_run_safe.xlsx`.
- **CẤM:** Không tự ý xóa thư mục manifests, cohorts, snapshot_bundles hoặc journal trong cron sync; không tự ý gọi lại picker hay tái sinh manifest làm sai lệch digest của các batch feed runner đang chạy.

## 2. Gate 4c: Upload Cooldown & Age Verification (Tik 5, Tik 6 & Rows >= 5)
- **Quy tắc:**
  1. Rows 1..4 (Tik 1..4): Đã trưởng thành, đủ điều kiện upload ngay lập tức (`is_eligible = True`).
  2. Rows >= 5 (Tik 5, Tik 6 và các ca mới sau này):
     - Không được upload video khi nick chưa đủ 10 ngày tuổi.
     - Với nick hiện tại: lấy mốc tối thiểu `2026-09-11` (10 ngày kể từ 01/09/2026).
     - Với nick tạo mới: `min_allowed_date = max(created_date + 10 days, 2026-09-11)`.
     - **Fail-closed:** Nếu không đọc được ngày tạo (DAT thiếu/lỗi hoặc không có ngày), trả về `is_eligible = False`, `reason = "account_creation_date_unverifiable"`.
- **Watchdog Classification:**
  - Watchdog (`feed_session_watchdog.py`) nhận diện các lý do skip liên quan đến cooldown (`cooling_period`, `account_cooling_period`, `age_gate`, `under_10_days`) để phân loại vào nhóm `up_skipped`, không báo lỗi giả (`up_failed`).
