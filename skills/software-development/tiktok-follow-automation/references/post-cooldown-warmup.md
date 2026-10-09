# Post-Cooldown Warmup Contract & Session Budget

## Context & Motivation
Sau khi nick hoàn tất thời gian ngâm cooldown (48h/96h/7d do nhả follow hoặc vi phạm streak), nếu lập tức cấp full quota (6-10 follow/session), nick có rủi ro cao tiếp tục bị TikTok đánh dấu hành vi bất thường và nhả follow ngay trong lượt đầu.

Do đó, hệ thống áp dụng cơ chế **Post-Cooldown Warmup**:
- Thăm dò follow với số lượng nhỏ, thận trọng.
- Khi nick thực hiện follow thành công đầu tiên, `mark("uid", STATUS_FOLLOWED)` sẽ reset `fail_streak = 0`, chính thức đưa nick trở lại trạng thái bình thường (full budget).

## Contract Definition

### 1. State Property: `is_post_cooldown_warmup`
Nằm trong `follow_runner/core/follow_state.py`:
```python
@property
def is_post_cooldown_warmup(self) -> bool:
    """Nick vừa mãn hạn cooldown: từng bị phạt (fail_streak > 0) nhưng hiện đã hết hạn (follow_failed == False)."""
    return self.fail_streak > 0 and not self.follow_failed
```

### 2. Session Budget Thăm Dò
Trong `session_budget(video_count)`:
- Nếu `video_count >= 5` (đạt video gate):
  - Nếu `self.is_post_cooldown_warmup`: trả về `random.randint(3, 5)`.
  - Nếu bình thường: trả về `_range(1)` (full 6-10 theo config).
- Nếu `video_count < 5` hoặc `None`: luôn trả về `0`.

### 3. Exit Condition
- Khi follow thành công 1 user bất kỳ: `FollowState.mark(uid, STATUS_FOLLOWED)` reset `fail_streak = 0`.
- Khi đó, `is_post_cooldown_warmup` tự động trở về `False` và các phiên kế tiếp nhận full budget.
