# Follow Gate & Re-entry Pull-to-Refresh Verification

## Cơ chế kiểm tra nhả Follow bằng Pull-to-Refresh (Mode 2)
Trong `tiktok-follow` (`follow_runner/flows/mode2_follow_followers.py`):
- Khi chạy Follow Followers (Mode 2), trước khi cào follower của Anchor, script kiểm tra và đảm bảo đã follow Anchor (`_ensure_anchor_followed`).
- Để tránh bị TikTok cache client đánh lừa (sau khi tap Follow trên video hoặc profile, UI vẫn hiện `Nhắn tin`), script bắt buộc thực hiện **Pull-to-refresh (vuốt kéo reload profile)**:
  1. Mở video đầu tiên của Anchor -> Tap Follow trên video.
  2. Bấm Back quay lại Profile.
  3. Gọi `pull_to_refresh_profile` (vuốt kéo từ trên xuống dưới có jitter tự nhiên).
  4. Recapture UI dump và kiểm tra trạng thái nút hành động:
     - Nếu chuyển về `followed` (`Nhắn tin` / `Đã follow`) -> Tiếp tục cào follower.
     - Nếu chuyển về `not_followed` (`Follow` đỏ / `Theo dõi`) -> Kết luận nick bị phạt nhả follow (`FOLLOW_FAILED`) và dừng session.

## Cảnh báo rò rỉ Follow qua Popup Handler ở Feed Session
Mặc dù `multi_machine_feed_session.py` đã chặn gọi `run_follow.py` cho các nick chưa đủ điều kiện (< 6 video, < 21 ngày, organic rest), các popup handler trong `benign_popup.py` và `feed_swipe_smoke.py` (`follow_back_suggestion`) cần được kiểm tra điều kiện tương tự để không tự ý bấm follow khi lướt feed.
