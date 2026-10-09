# Video Gate & Post-Cooldown Warmup Discipline (15/09/2026)

## 1. Gate >= 10 Video Đã Đăng (Nâng từ 5 lên 10)
- **Mục đích**: Bảo vệ nick mới / nick ít video khỏi bị TikTok shadow-ban (nhả follow) ngay sau khi bấm.
- **Tầng Follow Runner (`follow_state.py`)**:
  - `session_budget(video_count)`: Kiểm tra `video_count is not None and int(video_count) >= 10`.
  - Dưới 10 video hoặc None -> ép thẳng `budget = 0`.
- **Tầng Lọc Anchor (`follow_engine.py`)**:
  - Chỉ các nick nội bộ có `row_video_counts >= 10` mới được đưa vào danh sách anchor follow chéo.
- **Tầng Feed Session Hook (`multi_machine_feed_session.py`)**:
  - Kiểm tra `video_count < 10` ngay trước khi gọi hook follow.
  - Skip ngay với lý do `under-10-videos-follow-disabled`, ghi nhận kết quả an toàn.

## 2. Quy Tắc Dưỡng Nick Hồi Phục Sau Phạt Nhả (Post-Cooldown Warmup)
- **Hiện tượng**: Nick hết hạn cooldown (`fail_streak > 0`, `follow_failed == False`) bắt đầu được thả ra follow lại.
- **Budget dò nhẹ**: Chỉ cấp **3 đến 5 lượt/phiên** (`is_post_cooldown_warmup`).
- **Lỗ hổng cần tránh (Pitfall)**:
  - Khi nick follow thành công 1 lượt đầu tiên, TUYỆT ĐỐI KHÔNG xóa `fail_streak = 0` ngay trong `mark()`.
  - Nếu xóa ngay, cờ `is_post_cooldown_warmup` bị mất, các phiên tiếp theo trong cùng ngày sẽ bị cấp full budget (15-20 lượt) khiến nick lập tức bị phạt tái diễn (`fail_streak = 2` hoặc `3`).
  - **Kỷ luật**: Giữ nguyên `fail_streak` trong suốt ngày hôm đó. Chỉ reset `fail_streak = 0` khi hệ thống roll sang ngày mới (`_roll_day()`) sau khi nick đã trải qua 1 ngày dưỡng trọn vẹn.
