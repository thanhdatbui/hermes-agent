# Unified Follow Dual Gate Rules & Watchdog Reconciliation

## 1. Nguyên Tắc Cốt Lõi: Single Source of Truth
CẤM TUYỆT ĐỐI duy trì 2 bộ điều kiện riêng rẽ giữa **Follow Tự Nhiên** (lướt feed) và **Follow Chéo** (hook sau feed).
Mọi hành vi follow của tài khoản phải tuân thủ đúng 1 bộ điều kiện Dual Gate:

| Điều Kiện | Tiêu Chuẩn | Nếu Không Đạt |
|---|---|---|
| **Organic Rest** | Không phải ngày dưỡng sinh (~33% máy nghỉ follow/up) | Khóa `_follow_rate = 0`, skip follow-hook |
| **Follow Cooldown** | `is_account_in_follow_cooldown` = False (không bị phạt nhả follow) | Khóa `_follow_rate = 0`, skip follow-hook |
| **Video Count** | `video_count >= 6` video đã đăng | Khóa `_follow_rate = 0`, skip follow-hook (`under-6-videos-follow-disabled`) |
| **Account Age** | `account_age_days >= 21` ngày tính từ `Ngày Tạo` | Khóa `_follow_rate = 0`, skip follow-hook (`under-21-days-follow-disabled`) |
| **Missing Age Fallback** | Nếu workbook không có cột ngày tạo: yêu cầu `video_count >= 10` | Khóa `_follow_rate = 0`, skip follow-hook |

## 2. Điểm Kích Hoạt Trong Code (`tiktok-luot nuoi acc`)
- **`python_runner/core/feed_session_workbook.py`**:
  - Nhận diện `DATE_COLUMNS` (`ngay tao`, `ngày tạo`, `created at`, `ngay`, `date`).
  - Parse ngày ISO và tính `account_age_days = (today - created_date).days`.
  - Nạp `created_date` và `account_age_days` vào `MachineAccount`.
- **`python_runner/flows/multi_machine_feed_session.py`**:
  - `_run_child`: Truyền `_account_age_days` vào `child_config`. Nếu `account_age_days < 21` hoặc `video_count < 6` hoặc `is_organic`: gán `child_config["_follow_rate"] = {"for_you": 0, "following": 0, "friends": 0}`.
  - `_run_follow_hook`: Kiểm tra sớm `account_age_days < 21` -> skip với reason `under-21-days-follow-disabled`, không gọi subprocess.
- **`python_runner/flows/feed_swipe_smoke.py`**:
  - `_maybe_follow_video`: Kiểm tra `_account_age_days < 21` -> log telemetry skipped `account has under 21 days age (natural follow disabled)` và return False.
- **`scripts/feed_session_watchdog.py`**:
  - Nhận diện `under-21-days` vào nhóm `Chưa đủ điều kiện`.

## 3. Quy Tắc Báo Cáo Đối Soát TikTok Web (Watchdog)
- **Ẩn nick không lệch**: Chỉ đưa vào danh sách chi tiết các tài khoản có `diff != 0` (lệch số follow script báo vs web tăng) hoặc thiếu snapshot (`UNPROVEN`).
- **Không spam dòng Khớp**: Các nick `diff == 0` (KHỚP; chênh lệch +0) không được in chi tiết trong report.
- **Không nhầm lẫn tag code**: Tag `mode2_zero_following_fix: zero-following-skip-v2` chỉ là tên version tính năng trong `details`, không phải bằng chứng anchor bị 0 following.
