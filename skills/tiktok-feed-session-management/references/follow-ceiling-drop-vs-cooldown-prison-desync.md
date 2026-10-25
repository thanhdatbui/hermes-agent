# Phân Định Chạm Trần Phiên (Ceiling Drop) vs Đi Tù (Cooldown Prison) & Lệch Pha Đa Repo

## 1. Bản Chất Kỹ Thuật: Chạm Trần Phiên vs Lỗi Nhả Thật
- **Chạm trần phiên (`used > 0`):**
  - Tài khoản đã bấm follow thành công $\ge 1$ nick sạch trong phiên (ví dụ 2/3, 3/4, 4/5) rồi mới bị TikTok ngắt ở lượt cuối cùng.
  - Đây là giới hạn tải (sliding window / rate limit) tạm thời của TikTok trong ngày, **KHÔNG PHẢI tài khoản vi phạm spam hay bị phạt**.
  - **Quy tắc vàng:** Tài khoản đã follow được thì **tuyệt đối KHÔNG tính là đi tù** (không tăng `fail_streak`, không giam cooldown 3–15 ngày, không thu hồi cờ `graduated`, không xóa `probation_clean_days`). Chỉ cần nghỉ xả cache trong ngày hôm đó (hoặc tối đa 1 ngày).
- **Nhả follow thật sự (`used == 0`):**
  - Vừa vào bấm nick đầu tiên (hoặc Anchor) đã bị TikTok từ chối ngay lập tức $\rightarrow$ tài khoản chưa có độ tin cậy hoặc đang dính cờ bot thực sự. Lúc này mới áp dụng cơ chế lũy tiến backoff `fail_streak` (3d -> 5d -> 7d -> 15d).

## 2. Tử Huyệt Lệch Pha Cooldown Giữa 2 Repo (`tiktok-follow` vs `tiktok-luot nuoi acc`)
- **Nguyên nhân gây giam oan ngầm:**
  1. Trong `follow_runner/core/follow_state.py` (`tiktok-follow`), khi `used > 0`, code chỉ gán `cooldown_until_date` là ngày mai (1 ngày xả cache).
  2. Tuy nhiên, trong `python_runner/flows/multi_machine_feed_session.py` (`tiktok-luot nuoi acc`), hàm `_is_account_follow_cooldown()` lại độc lập kiểm tra:
     ```python
     if state.get("follow_failed"):
         streak = int(state.get("fail_streak", 1) or 1)
         streak_days = 3 if streak <= 1 else (5 if streak == 2 else 7)
         is_in_cooldown = is_in_cooldown or today <= failed_day + timedelta(days=streak_days)
     ```
  3. Đoạn hardcode trên phớt lờ hoàn toàn `cooldown_until_date = 1 ngày` của `follow_state.py`, tự động ép tài khoản vào án phạt 3–7 ngày dựa theo `fail_streak` cũ, khiến máy bị skip follow hook oan liên tiếp nhiều ngày.
- **Nguyên tắc đồng bộ:**
  - `multi_machine_feed_session.py` BẮT BUỘC phải tôn trọng tuyệt đối `cooldown_until_date` và `cooldown_until_at` do `follow_state.py` ghi nhận, cấm tự suy diễn thêm `streak_days` khi state đã xác định thời hạn nghỉ.

## 3. Quy Trình Đối Soát & Xả Án Bằng `reconcile_unfair_streaks.py`
- Khi kiểm tra tỷ lệ nick dính cooldown/streak dài toàn farm:
  1. Chạy dry-run rà soát: `python D:/Taadaa/tools/reconcile_unfair_streaks.py --dry-run`.
  2. Phân loại 2 nhóm:
     - `A_CEILING_DROP`: Có `followed >= 1` vào ngày dính cờ fail (chạm trần nhưng bị đè án phạt).
     - `B_TRAPPED_HIGH_TRUST`: Nick khỏe có tổng followed $\ge 10$ nhưng bị kẹt streak $\ge 2$ hoặc cooldown quá hạn.
  3. Thực thi xả án để khôi phục về `fail_streak = 1`, `follow_failed = False`, `probation_clean_days = 1`.
