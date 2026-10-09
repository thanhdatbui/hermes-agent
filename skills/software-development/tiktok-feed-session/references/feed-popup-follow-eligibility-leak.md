# Feed Session Popup & Follow Back Safety Pitfall

## Vấn đề phát hiện (2026-10-07)
Khi chạy lướt feed trên các máy mới / chưa đủ điều kiện follow (như dàn Admin 201-280 với < 6 video hoặc tuổi < 21 ngày, hoặc ngày nghỉ dưỡng sinh organic rest):
- Flow chính `multi_machine_feed_session.py` (Follow Hook) đã chặn đúng `under-6-videos-follow-disabled` (exit status `skipped`, `followed_count = 0`).
- Tuy nhiên trong quá trình lướt feed, tài khoản vẫn có thể bị bấm follow nhầm do các bộ xử lý popup sau:
  1. `dismiss_follow_friends_suggestion_popup` trong `benign_popup.py` (bấm tối đa 2 nút "Follow lại" / "Follow" bạn bè trước khi đóng popup).
  2. Rule `follow_back_suggestion` trong `feed_swipe_smoke.py` (tự động tap nút "Follow lại" / `fij` / `cv4` khi quét thấy trên màn hình / feed video).

## Nguyên nhân gốc rễ
Các handler popup trên chỉ mới kiểm tra cổng `is_account_in_follow_cooldown(ctx)` (kiểm tra có đang bị phạt nhả follow hay không), mà **chưa kiểm tra toàn diện điều kiện follow của tài khoản**:
- Tuổi acc (`_account_age_days < 21`).
- Số video (`_video_count < 6`).
- Ngày dưỡng sinh (`_is_organic_rest` / `rest_day_no_follow`).

## Yêu cầu thiết kế chuẩn cho mọi popup handler liên quan đến Follow
Bất kỳ logic nào có hành động tap `Follow` / `Follow lại` / `Follow back` trong `benign_popup.py`, `feed_swipe_smoke.py` hoặc các flow feed BẮT BUỘC phải tuân thủ điều kiện:
```python
# Điều kiện chặn toàn diện:
if (
    is_account_in_follow_cooldown(ctx)
    or getattr(ctx, "config", {}).get("_is_organic_rest")
    or getattr(ctx, "config", {}).get("rest_day_no_follow")
    or (getattr(ctx, "config", {}).get("_account_age_days") is not None and int(getattr(ctx, "config", {}).get("_account_age_days")) < 21)
    or (getattr(ctx, "config", {}).get("_video_count") is not None and int(getattr(ctx, "config", {}).get("_video_count")) < 6)
):
    # Chỉ dismiss/bỏ qua, tuyệt đối CẤM tap nút Follow / Follow lại!
```
