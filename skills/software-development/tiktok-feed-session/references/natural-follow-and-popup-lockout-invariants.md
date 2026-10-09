# Quy Tắc Khóa Triệt Để Follow Tự Nhiên & Popup Gợi Ý Trên TikTok Feed (2026-10-07)

## 1. Bối cảnh & Hiện tượng lỗi
- Trong quá trình lướt Feed (`tiktok-luot nuoi acc`), một số máy Admin hoặc nick non chưa đủ điều kiện follow (chưa đủ 6 video / < 21 ngày tuổi) vẫn bị bấm follow nhầm do:
  1. Handler popup gợi ý bạn bè (`dismiss_follow_friends_suggestion_popup` trong `benign_popup.py`) cho phép follow 1-2 bạn trước khi đóng nếu không dính cooldown.
  2. Rule blind popup `follow_back_suggestion` trong `feed_swipe_smoke.py` tự động bấm nút "Follow lại" nếu tài khoản sạch (không dính cooldown).
- Hậu quả: Dàn Admin hoặc tài khoản chưa đủ điều kiện bị bấm follow tự nhiên vãng lai, vi phạm quy tắc an toàn farm và gây rủi ro nhả follow ngầm.

## 2. Quy chuẩn kỹ thuật xử lý (Invariant)

### A. Khóa follow tự nhiên trong Popup Gợi ý bạn bè (`benign_popup.py`)
- Trong `dismiss_follow_friends_suggestion_popup`:
  + Đặt cứng `follow_limit = 0`.
  + Handler chỉ tập trung tìm control đóng popup: nút `X` / Đóng ngữ nghĩa, hoặc navigation back (`id/bq7`, `send_device_back_key(ctx)`).
  + Tuyệt đối không click vào bất kỳ nút `Follow`, `Follow lại`, `Theo dõi lại` nào trong popup.

### B. Khóa follow tự nhiên trên Thẻ đề xuất trên Feed (`feed_swipe_smoke.py`)
- Trong rule `follow_back_suggestion` (blind popup handler):
  + Tuyệt đối không tap nút detector (`Follow lại`).
  + Luôn luôn tìm và tap nút **"Không quan tâm"** (`resource-id="com.ss.android.ugc.trill:id/cv6"` hoặc `@text="Không quan tâm"`) để ẩn thẻ khỏi feed.

### C. Kiểm tra an toàn đa tầng trong `is_account_in_follow_cooldown` (`feed_swipe_smoke.py`)
- Hàm `is_account_in_follow_cooldown(ctx)` bắt buộc kiểm tra các điều kiện:
  1. Cờ `_follow_cooldown` trong config context.
  2. Ngày nghỉ dưỡng sinh: `_is_organic_rest` hoặc `rest_day_no_follow`.
  3. Tuổi nick: `_account_age_days < 21`.
  4. Số lượng video: `_video_count < 6`.
  5. File state: `follow_state_<machine>_row_<row>.json` (cooldown_until_at, cooldown_until_date, follow_failed_date, follow_blocked).
- Bất kỳ điều kiện nào không thỏa mãn -> Coi tài khoản đang trong diện bị khóa follow (`in_cooldown = True`), hủy bỏ mọi hành động follow video vãng lai.
