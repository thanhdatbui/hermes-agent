# Xử lý Lỗi Chuyển Tab Feed (Friends / Following Target Unavailable)

## Bối cảnh & Vấn đề
- Trong luồng nuôi acc (`feed_swipe_smoke.py` / `feed_session_smoke`), session có cơ chế phân bổ feed ngẫu nhiên (`_weighted_feed_choice(feed_distribution)`) để đổi sang `friends` hoặc `following`.
- Trên nhiều thiết bị hoặc layout giao diện TikTok mới/tài khoản chưa kết bạn, tab "Bạn bè" (`Friends`) không xuất hiện trên UI (hoặc XML không tìm thấy node tương ứng).
- Khi gọi `tap_navigation_target(ctx, _top_tab_target(next_feed_type), ...)`, kết quả trả về `navigation.ok == False` (`navigation target friends not found in XML`).

## Nguyên tắc Xử lý & Phục hồi (Graceful Degradation)
1. **Không ngắt phiên**:
   - Khi `not navigation.ok` do tab mục tiêu không tồn tại trên XML/UI, **CẤM** ngắt phiên hay trả về failure ngay (`finalize_feed_session_cleanup`).
2. **Fallback về Feed hiện tại**:
   - Ghi nhận `ctx.logger.log` cảnh báo (`result="warning"`).
   - Đánh dấu row status là `DEGRADED` (hoặc retain feed hiện tại).
   - Giữ nguyên `current_feed_type` (thường là `for-you`) và để vòng lặp swipe tiếp tục lướt các video tiếp theo cho đến khi hoàn thành 100% `total_swipes_requested`.
3. **Unit Test Bắt buộc**:
   - Mọi thay đổi luồng đổi tab phải được bảo vệ bởi test case (ví dụ `test_feed_session_skips_and_continues_feed_when_target_tab_not_found_in_xml` và `test_feed_session_falls_back_to_for_you_when_friends_navigation_stays_on_following`).
