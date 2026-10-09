# Quy tắc Preflight Age Gate / Cooldown đăng video TikTok

## Context
Trong quy trình kiểm tra điều kiện đăng video (`upload_preflight.py` thuộc `tiktok-luot nuoi acc/python_runner/flows/upload_preflight.py`):
- `check_upload_cooldown_eligibility(machine, row_index, ...)` kiểm tra điều kiện độ tuổi tài khoản trước khi cho phép tiến hành flow đăng video.

## Quy tắc
1. **Ca cũ / Nick trưởng thành (Row 1..4 - Tik 1..4)**:
   - Luôn đủ điều kiện (`True, "ok", current_date`).
2. **Ca mới (Row >= 5 - Tik 5, Tik 6...)**:
   - Có ngày tạo (`created_date is not None`): Áp dụng thời gian làm nguội tối thiểu 3 ngày (`CREATION_COOLDOWN_DAYS = 3`) hoặc mốc benchmark (`BENCHMARK_MIN_UPLOAD_DATE = 2026-09-11`). Nếu chưa đủ ngày thì chặn `account_cooling_period_until_<date>`.
   - **Để trống ngày tạo (`created_date is None`)**: Coi như nick cũ reg lâu rồi, cho phép đăng video luôn (`True, "ok", current_date"`), không chặn dạng `account_creation_date_unverifiable`.
