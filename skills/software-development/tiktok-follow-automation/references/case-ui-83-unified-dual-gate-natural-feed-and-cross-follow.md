# Case UI-83: Thống Nhất Dual Gate Follow Giữa Lướt Feed Và Follow Chéo (2026-10-02)

## 1. Hiện Tượng & Vấn Đề
- Trong ca nuôi feed, báo cáo watchdog ghi nhận có **7 lượt follow tự nhiên** (ví dụ M19, M51, M63) trong khi Follow Chéo là 0 lượt.
- Khi đối soát TikTok Web: M51 lệch -3, M63 lệch -1 (web tăng +0). Đồng thời nick không lệch (như M19 lệch +0) vẫn bị in vào danh sách báo cáo gây nhiễu.
- **Root Cause:**
  - Repo `tiktok-follow` áp dụng **Dual Gate 25/09**: Bắt buộc `account_age_days >= 21` VÀ `video_count >= 6`. Các nick Row 8 (tạo 16/09, mới 16 ngày tuổi) được cấp `budget = 0` nên không chạy follow chéo.
  - Repo `tiktok-luot nuoi acc` lại chỉ mới kiểm tra `video_count >= 6` khi lướt feed (bỏ sót tuổi tài khoản). Do nick đã có 6 video, script vẫn roll 5% follow tự nhiên và bấm nút trên feed. Tuy nhiên do nick < 21 ngày tuổi, server TikTok không ghi nhận (shadow-revert).

## 2. Giải Pháp Triệt Để: Single Source of Truth
CẤM TUYỆT ĐỐI duy trì 2 logic gate tách rời giữa Follow Tự Nhiên và Follow Chéo:
1. **Đồng bộ Workbook Metadata:**
   - `python_runner/core/feed_session_workbook.py` tự động đọc cột `Ngày Tạo` (`DATE_COLUMNS`), parse ngày chuẩn ISO và tính `account_age_days`.
2. **Đồng bộ Gating Flow:**
   - `python_runner/flows/multi_machine_feed_session.py`:
     - Khóa `_follow_rate = 0` ngay từ `_run_child` nếu `account_age_days < 21` hoặc `video_count < 6` hoặc `is_organic_rest`.
     - Trong `_run_follow_hook`: Bỏ qua sớm với lý do chuẩn `under-21-days-follow-disabled` (không khởi động subprocess vô ích).
   - `python_runner/flows/feed_swipe_smoke.py`:
     - Bổ sung kiểm tra `_account_age_days < 21` trong `_maybe_follow_video` để chặn triệt để hành vi bấm follow trên feed.
3. **Đồng bộ Watchdog Report:**
   - Ẩn toàn bộ các tài khoản đối soát khớp 100% (`diff == 0` / `chênh lệch +0`).
   - Chỉ report các tài khoản bị lệch số liệu (`diff != 0`) hoặc thiếu baseline snapshot (`UNPROVEN`).
   - Phân loại `under-21-days` vào nhóm `Chưa đủ điều kiện`.

## 3. Không Nhầm Lẫn Tag Version Code
- Tag `mode2_zero_following_fix: zero-following-skip-v2` chỉ là định danh version tính năng trong `res.details`, không phải bằng chứng anchor bị 0 following. Anchor Tik1/Tik2 của farm luôn có danh sách following đầy đủ.
