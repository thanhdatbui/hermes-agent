# Tracking Machine Quota & Eligibility Rules

## Quy tắc đếm slot máy (load_registered_mailboxes)
Trong `scripts/tiktok_target_eligibility.py`:
- Quota máy (`machine_counts[m]`) **chỉ được cộng khi dòng tracking có `tiktok_id` thật sự hợp lệ** (không rỗng / None).
- Các dòng placeholder hoặc dòng cấp phát trước nhưng chưa có nick (`tiktok_id` trống) **không** được tính là slot đã chiếm.
- Điều này đảm bảo `select_pending_targets` luôn chọn đúng các máy còn thiếu account (`count < max_accounts_per_machine`) để reg bù đủ quota.
