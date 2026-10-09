# Video Gate & Post-Cooldown Warmup Retention Policy

## 1. Video Gate Policy (>= 10 Videos)
- **Quy tắc an toàn**: Nick phải đạt tối thiểu 10 video đã đăng (`video_count >= 10`) mới được tham gia luồng follow (tránh tình trạng nick non chưa đủ trust bị shadowban hoặc nhả follow hàng loạt).
- **Phạm vi đồng bộ bắt buộc**:
  - `follow_runner/core/follow_state.py`: `session_budget()` kiểm tra `video_count >= 10`. Nếu `< 10` hoặc `None`, budget = 0.
  - `follow_runner/flows/follow_engine.py`: lọc anchor/uids (`row_video_counts.get(...) >= 10`).
  - `multi_machine_feed_session.py`: gate trước khi gọi hook follow (`video_count < 10` -> skip với action `skip_follow_under_10_videos` và reason `under-10-videos-follow-disabled`).

## 2. Post-Cooldown Warmup Retention Policy
- Khi tài khoản vừa mãn hạn cooldown (`is_post_cooldown_warmup == True`: `fail_streak > 0` và `follow_failed == False`):
  - **Budget áp dụng**: Giới hạn trong khoảng cữ nhẹ (3 - 5 lượt follow) cho toàn bộ các phiên trong ngày đầu tiên mở lại.
  - **Giữ trạng thái Warmup qua nhiều phiên**: Không được xóa `fail_streak = 0` ngay ở lượt follow thành công đầu tiên trong ngày, vì sẽ làm mất cờ warmup của các phiên tiếp theo cùng ngày.
  - **Reset Streak an toàn**: `fail_streak` chỉ được reset về 0 khi qua ngày mới (`_roll_day()`) sau khi đã hoàn thành trọn vẹn ngày chạy warmup mà không phát sinh thêm lỗi follow nào (`not follow_failed`).
