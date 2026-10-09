# Gate 10 Videos & Post-Cooldown Warmup Recovery (Spec 2026-09-15)

## 1. Gate Video >= 10 mới được đi Follow (`under-10-videos-follow-disabled`)
- **Quy tắc**: Mọi tài khoản có `video_count < 10` (hoặc None/chưa đủ 10 video đã đăng) bắt buộc phải bị skip an toàn ở tất cả các khâu:
  1. `FollowState.session_budget(video_count)`: Kiểm tra `video_count is not None and int(video_count) >= 10`. Nếu `< 10` trả về `0` budget.
  2. `FollowEngine`: Lọc danh sách anchor UIDs nội bộ `row_video_counts.get(...) >= 10`.
  3. `multi_machine_feed_session.py`: Kiểm tra trước khi gọi hook follow, nếu `video_count < 10` thì ghi nhận kết quả `status: "skipped"`, `reason: "under-10-videos-follow-disabled"` và không khởi chạy runner.

## 2. Chu trình Dưỡng Nick Sau Phạt (`Post-Cooldown Warmup`)
- **Vấn đề đã khắc phục**:
  - Khi nick mãn hạn phạt nhả follow (`fail_streak > 0` và `follow_failed == False`), nick rơi vào trạng thái `is_post_cooldown_warmup` với budget dò nhẹ chỉ từ **3 đến 5 follow/phiên**.
  - Trước đây, trong `FollowState.mark(uid, STATUS_FOLLOWED)`, hệ thống vội vã gọi `self._data["fail_streak"] = 0` ngay ở lượt follow thành công đầu tiên. Điều này xóa mất cờ warmup, khiến các phiên chạy tiếp theo trong cùng ngày bị đẩy vọt lên full budget (15–20 lượt), dẫn tới nguy cơ bị TikTok shadow-block lại ngay lập tức.
- **Quy chuẩn chuẩn hóa**:
  - Trong `mark(STATUS_FOLLOWED)`: Xóa các cờ lỗi (`follow_failed = False`, `cooldown_until_at = None`...), nhưng **GIỮ NGUYÊN `fail_streak`** trong suốt ngày hôm đó.
  - Trong `_roll_day()`: Khi ngày chuyển sang ngày mới (`budget_date != today`), nếu `follow_failed == False` (đã hoàn thành ngày warmup an toàn), lúc này mới reset `fail_streak = 0` và đưa nick trở lại trạng thái bình thường.

## 3. Thống kê thực tế về Hồi phục sau Phạt Nhả Follow (Dữ liệu Farm Kibe)
- **Tỷ lệ hồi phục chung**: ~12.8% (trên 179 nick từng bị phạt nhả).
- **Phân bố theo Row**:
  - Row 1 (Acc lâu năm, >= 10 video): Tỷ lệ hồi phục đạt **15.6%**.
  - Row 2 (Acc trung bình): Tỷ lệ hồi phục đạt **23.5%**.
  - Row 3, Row 4 (Acc mới ít video): Tỷ lệ hồi phục = **0.0%** (liệt chuỗi streak >= 3).
- **Thời gian cần để hồi phục**:
  - `fail_streak = 1` (phạt lần đầu): Cooldown 24h, hồi phục sau **1–2 ngày**.
  - `fail_streak = 2` (phạt lần 2): Cooldown 4 ngày, hồi phục sau **4–5 ngày**.
  - `fail_streak >= 3` (phạt dồn dập): Cooldown 7 ngày, hồi phục sau **7–10 ngày**.
