# Case 165: Phân Nhánh Follow Tự Nhiên & Thẻ Follow Lại Theo Trạng Thái Cooldown

## Bối cảnh & Vấn đề
- Trước đây, quy tắc `GemPhoneFarmBlindPopupRule` xử lý thẻ đề xuất tài khoản / bạn bè trên Feed (`follow_back_suggestion`) chặn vô điều kiện (`unconditional`) bằng cách luôn luôn tap vào nút "Không quan tâm" để đóng thẻ.
- Điều này dẫn tới việc cả các nick sạch (không bị phạt) cũng bị tước mất cơ hội follow lại tự nhiên để tăng tương tác tài khoản.

## Cơ chế nhận diện Cooldown (`is_account_in_follow_cooldown`)
- Hàm `is_account_in_follow_cooldown(ctx)` trong `python_runner/flows/feed_swipe_smoke.py:13669` đọc file state tại `D:/Taadaa/tiktok-follow/runs/state/`:
  - `follow_state_{machine}_row_{row}.json` (ưu tiên)
  - `follow_state_{machine}.json` (fallback)
- Kiểm tra 4 điều kiện:
  1. `cooldown_until_at`: so sánh UTC ISO timestamp (`now_utc < until_dt`).
  2. `cooldown_until_date`: so sánh chuỗi ngày (`today_str <= cooldown_until_date`).
  3. `follow_failed_date == today_str`: ghi nhận vừa thất bại trong ngày.
  4. `follow_failed is True`: cờ catch-all khi chưa có hạn ngày cụ thể.

## Ma trận hành vi Follow tự nhiên

| Luồng tương tác | Nick đang bị phạt nhả follow (`in_cooldown=True`) | Nick sạch (`in_cooldown=False`) |
|---|---|---|
| **Lướt Feed Đề xuất (For You)** | Chặn 100% (ép rate về 0%), log `skipped / account is in follow cooldown` | Tỷ lệ 5% (`DEFAULT_FEED_FOLLOW_RATES`), tìm nút Follow và tap |
| **Popup đề xuất bạn bè (Follow Friends)** | `follow_limit = 0`, không bấm ai, đóng popup bằng X / Back | `follow_limit = 2`, bấm tối đa 2 bạn bè rồi mới đóng popup |
| **Thẻ đề xuất trên Feed (`follow_back_suggestion`)** | Tap nút "Không quan tâm" (`com.ss.android.ugc.trill:id/cv6`) | Tap node detector ("Follow lại" / "Theo dõi lại") để tương tác |
| **Thẻ tab Bạn bè / Danh bạ** | Chuyển về Home hoặc vuốt feed khôi phục (không follow) | Chuyển về Home hoặc vuốt feed khôi phục (không follow) |

## File & Vị trí code
- `python_runner/flows/feed_swipe_smoke.py:4333-4342`: Phân nhánh thẻ `follow_back_suggestion` trong `_gem_blind_action`.
- `python_runner/flows/feed_swipe_smoke.py:13669`: Hàm `is_account_in_follow_cooldown`.
- `python_runner/flows/feed_swipe_smoke.py:13717`: Hàm `_maybe_follow_video`.
- `python_runner/flows/benign_popup.py:4920`: Hàm `dismiss_follow_friends_suggestion_popup`.
- `python_runner/tests/test_feed_swipe_smoke_popups.py`: Unit tests xác thực cả 2 nhánh (clean vs cooldown).
