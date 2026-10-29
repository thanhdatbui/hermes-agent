# Follow Detail Matrix Drop-Day Invariant & Zero-Follow Failure Pitfall

## Bối Cảnh (Context)
- Trong Dashboard TikTok Farm (port 1905), popup "Sổ bệnh án" (`get_account_follow_detail` trong `D:/Taadaa/tools/follow_health_helper.py`) hiển thị ma trận các ca chạy gần nhất (`daily_matrix`) cùng trạng thái an toàn / bị nhả.
- Tài khoản bị phạt cooldown / nhả follow ghi nhận `last_failed_date`, `fail_streak`, và `is_in_cooldown`.

## Vấn Đề Gặp Phải (Root Cause)
1. Khi tài khoản bị nhả follow ngay đầu phiên (ví dụ do bẫy Anchor Check nhả follow sau vuốt), runner dừng session ngay lập tức với `followed_count = 0`.
2. Do không có UID nào được follow thành công trong ngày đó, từ điển `followed` và `history` của file `follow_state_<m>_row_<r>.json` hoàn toàn không có entry cho ngày `drop_day` (`last_failed_date`).
3. Hàm `get_account_follow_detail` trước đây chỉ lặp qua `daily.keys()` (các ngày có follow > 0) để tạo `daily_matrix`. Hệ quả: `drop_day` bị bỏ qua hoàn toàn, Sổ bệnh án không hiển thị chip cảnh báo `🛑 0 lượt` (bị nhả), khiến User thấy bảng tổng quan báo có nhả/cooldown nhưng mở sổ bệnh án ra lại thấy trắng trơn lịch sử streak bị nhả.

## Khế Ước Bắt Buộc (Invariant Contract)
- **Nạp Drop-Day Vào Daily Matrix Dù Zero-Follow:**
  Trong `get_account_follow_detail`, sau khi xác định `drop_day` từ `last_failed_at`, `last_cooldown_decision`, hoặc `last_failed_date`:
  ```python
  if is_in_cooldown:
      ...
      if not drop_day:
          drop_day = (d.get("last_failed_date") or d.get("follow_failed_date") or "")[:10] or None
      if drop_day and drop_day not in daily:
          daily[drop_day] = 0
  ```
- **Bảo toàn lịch sử theo ngày chạy của nick (Per-Account Activity History):**
  Lịch sử ca chạy của từng tài khoản phải phản ánh đúng các mốc thời gian nick đó thực sự có hành động (chạy an toàn hoặc bị nhả follow/cooldown), không bị phụ thuộc vào việc ca đó có ăn follow nào hay không.
