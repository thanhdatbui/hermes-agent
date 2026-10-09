# Video Gate & Streak Recovery Rules (2026-09-15 update)

## 1. Video Gate Threshold (>= 10 videos)
- **Threshold**: Chỉ cho phép follow khi tài khoản có `video_count >= 10`.
- **Enforcement across repos**:
  - `tiktok-follow` (`follow_runner/core/follow_state.py`):
    - `session_budget(video_count)`: Nếu `video_count < 10` hoặc `None`, trả về `0`.
    - Khi `video_count >= 10`: nếu `is_post_cooldown_warmup` trả về `randint(3, 5)`, ngược lại trả về full range (6-10).
  - `tiktok-follow` (`follow_runner/flows/follow_engine.py`):
    - Lọc target UID yêu cầu `row_video_counts >= 10`.
  - `tiktok-luot nuoi acc` (`python_runner/flows/multi_machine_feed_session.py`):
    - Kiểm tra `video_count < 10`: Bỏ qua follow với payload:
      ```python
      {
          "status": "skipped",
          "reason": "under-10-videos-follow-disabled",
          "followed_count": 0,
          "failed": 0,
          "follow_failed": False,
      }
      ```
    - Action log: `skip_follow_under_10_videos`.

## 2. Failure Streak Preservation on Same-Day Recovery
- **Behavior in `mark("followed")`**:
  - Khi follow thành công, clear các cờ cooldown (`follow_failed`, `cooldown_until_at`, v.v.), nhưng **không** reset `fail_streak = 0` ngay lập tức.
  - Streak được giữ nguyên trong cùng ngày để kích hoạt `is_post_cooldown_warmup` (chạy ấm từ tốn 3-5 lượt).
- **Behavior in `_roll_day()`**:
  - `fail_streak` chỉ được reset về `0` khi sang ngày mới nếu `follow_failed` đang là `False`:
    ```python
    if not self._data.get("follow_failed", False):
        self._data["fail_streak"] = 0
    ```
