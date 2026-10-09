# Budget & 6-Day Rest Cycle Standard (Chốt 2026-09-15)

## 1. Budget Configuration Standards
- Áp dụng trên `follow_runner/config.example.yaml` và tất cả 17 machine configs (`config/machine*.yaml`):
  - `budget_per_day: 40` (follow/ngày/máy host clock)
  - `budget_per_session_min: 10`
  - `budget_per_session_max: 20`
  - `budget_per_session: 20`

## 2. Chu kỳ 6 ngày (6-Day Cycle) & Ngày nghỉ dưỡng sinh (Rest Day)
- **Cơ chế phân bổ slot**:
  - Máy chạy 24 accounts: 4 acc/ngày trong 5 ngày đầu (tổng 20 acc hoạt động follow).
  - Ngày thứ 6: Ngày nghỉ follow dưỡng sinh (Rest Day).
- **Quy tắc vận hành ngày nghỉ**:
  - Feed session (nuôi acc/lướt feed) vẫn diễn ra bình thường để duy trì trust score tự nhiên.
  - Follow hook bị bypass hoàn toàn thông qua cờ môi trường `TAADAA_REST_DAY_NO_FOLLOW=1` hoặc param `rest_day_no_follow=True` trong `multi_machine_feed_session.py`.
  - Cấm chạy upload hook hoặc follow hook trong ngày nghỉ dưỡng sinh để bảo vệ tài khoản khỏi nhả follow / checkpoint.
