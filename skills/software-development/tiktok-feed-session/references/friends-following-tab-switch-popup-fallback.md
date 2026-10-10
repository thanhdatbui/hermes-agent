# Friends & Following Tab Switch Popup Recovery & Graceful Fallback

## Ngữ cảnh & Triệu chứng
Trong phiên nuôi TikTok (`feed-session-smoke` / `multi-machine-feed-session`), runner có tỷ lệ nhất định chuyển tab từ For You sang tab **Friends** hoặc **Following** để tương tác tự nhiên.
Khi vừa tap chuyển tab:
- TikTok thường hiển thị các modal/popup dạng:
  - `contacts_settings_permission_dialog` (Hỏi quyền truy cập danh bạ để tìm bạn bè)
  - `contact_follow_suggestion` (Gợi ý follow danh bạ / bạn bè)
  - `feature_promo_overlay` / `sponsored_ad_feedback`
- Sau khi popup dismisser (allowlist hoặc gemphonefarm blind probe) cố gắng đóng popup, màn hình confirm chụp lại có thể vẫn còn dấu vết hoặc bị phân loại là `manual-needed:popup` / `unexpected popup/dialog marker detected`.

## Pitfall: ManualReasonGuard chẹn trước Fallback
Trước đây:
- Script bọc kiểm tra trong:
  ```python
  if manual_guard.record(_safety_from_row(ctx, confirm)):
      if next_feed_type in {FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS} and (
          confirm.get("detected") in {"manual-needed:network", "manual-needed:empty", "manual-needed:retry", "manual-needed:popup"}
          or _has_friends_feed_content(confirm)
      ):
          # fallback to For You
  ```
- Do `manual_guard.record()` đếm số lần liên tiếp cùng reason (`consecutive_count >= 2`), nếu bước trước đó vừa dính popup và bước sau vẫn mang `manual-needed:popup`, `manual_guard` trả về `True` nhưng nếu detected screen hoặc status chưa khớp danh sách hẹp thì session bị return abort `manual-needed` ngay lập tức!
- Hậu quả: Hàng loạt máy (6 máy Kibe, 19 máy Admin) bị ngắt phiên nuôi sớm với lỗi `Lỗi App TikTok/Script` (`stop_reason: unexpected popup/dialog marker detected`).

## Giải pháp chuẩn hóa (Graceful Fallback)
Khi chuyển tab sang Friends / Following:
1. Xác định `_need_tab_fallback`:
   ```python
   _need_tab_fallback = next_feed_type in {FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS} and (
       confirm.get("status") in {ExitStatus.MANUAL_NEEDED.value, "fail", "failed"}
       or confirm.get("safety_status") == SAFETY_MANUAL_NEEDED
       or confirm.get("detected") in {"manual-needed:network", "manual-needed:empty", "manual-needed:retry", "manual-needed:popup"}
       or _has_friends_feed_content(confirm)
   )
   ```
2. Nếu `_need_tab_fallback` thỏa mãn:
   - Ghi log cảnh báo `fallback_feed_tab`.
   - Tap chuyển ngay về tab For You (`tap_navigation_target(_top_tab_target(FEED_TYPE_FOR_YOU))`).
   - Đặt `current_feed_type = FEED_TYPE_FOR_YOU`, `next_feed_type = FEED_TYPE_FOR_YOU`.
   - Set `confirm["status"] = ExitStatus.DEGRADED.value`, `confirm["safety_status"] = "ok"`.
   - Đặt lại delay đếm video trước khi quyết định đổi tab tiếp theo (`random.randint(5, 10)`).
   - Session tiếp tục hoàn thành chỉ tiêu video thay vì bị ngắt quãng giữa chừng.
