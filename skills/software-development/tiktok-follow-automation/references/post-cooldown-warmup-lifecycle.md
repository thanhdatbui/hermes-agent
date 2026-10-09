# Post-Cooldown Warmup (3-5 Follows) State Lifecycle & Invariants

## Bối cảnh & Mục tiêu
Khi một tài khoản vừa mãn hạn cooldown (do dính progressive backoff sau khi bị nhả follow), tài khoản cần được chạy "làm ấm" (warmup) với ngân sách giới hạn 3–5 follow/phiên để kiểm tra độ ổn định của tài khoản trước khi cấp lại ngân sách đầy đủ (full budget: 6–10 hoặc 9–12).

## Cơ chế State (`follow_state.py`)
- **Điều kiện Warmup (`is_post_cooldown_warmup`)**:
  `self.fail_streak > 0 and not self.follow_failed`
  Nghĩa là: tài khoản từng bị phạt (`fail_streak > 0`), nhưng cooldown đã hết hạn (`follow_failed == False`).
- **Ngân sách Warmup**:
  Khi `is_post_cooldown_warmup == True` và video >= 5:
  `session_budget(video_count)` trả về `random.randint(3, 5)`.

## Pitfall nghiêm trọng: Xóa `fail_streak` ngay tại lượt follow thành công đầu tiên
- **Lỗi**: Trước đây, trong hàm `mark(uid, STATUS_FOLLOWED)`:
  ```python
  if status == self.STATUS_FOLLOWED:
      self._data["fail_streak"] = 0  # <-- LỖI: Xóa ngay lập tức
  ```
- **Hệ quả**:
  Ngay khi nick vừa follow thành công 1 người trong phiên sáng của ngày mãn hạn cooldown:
  1. `fail_streak` bị gán về 0.
  2. `is_post_cooldown_warmup` lập tức chuyển thành `False`.
  3. Tất cả các phiên còn lại trong ngày (phiên trưa, phiên tối) bị nhảy vọt về full budget (6–10 / 9–12) thay vì duy trì mức 3–5 follow nhẹ nhàng suốt cả ngày đầu tiên trở lại.

## Quy tắc chuẩn (Warmup Lifecycle Invariant)
1. **Trong ngày Warmup (`mark` success)**:
   - Khi `mark(uid, STATUS_FOLLOWED)` thành công: xóa `follow_failed = False` và các mốc cooldown (`cooldown_until_at`, `cooldown_until_date`, `last_failed_date`, `last_failed_at`, `follow_failed_date`).
   - **KHÔNG ĐƯỢC** reset `fail_streak = 0` tại `mark()`. Giữ nguyên `fail_streak` để `is_post_cooldown_warmup` luôn là `True` trong toàn bộ các cữ chạy còn lại của ngày hôm đó.
2. **Chuyển ngày (`_roll_day`)**:
   - Khi chuyển sang ngày mới (`budget_date != today`), `_roll_day()` kiểm tra: nếu tài khoản không còn bị phạt (`follow_failed == False`) và đã hoàn thành ngày làm ấm, `fail_streak` mới được reset về 0.
   - Từ ngày tiếp theo trở đi, tài khoản chính thức trở lại chế độ full budget bình thường.
