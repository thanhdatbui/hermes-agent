# Swipe Recovery on Stuck Pitfall & Enforcement

### 1. Nguyên tắc cốt lõi
- Mọi màn hình không nhận diện được / video quảng cáo toàn màn hình (In-Feed Ad, TopView) / popup lạ không nhạy cảm (không phải màn hình Login, Captcha, OTP):
  **BẮT BUỘC chạy cơ chế vuốt cứu kẹt (`_swipe_recovery_on_stuck` 1-2 lần) TRƯỚC KHI gọi `manual_guard.record()` hoặc `finalize_feed_session_cleanup`**.

### 2. Các điểm cần đảm bảo trong luồng chạy (`_feed_session_flow`)
1. **Giai đoạn `baseline`:** Khi vừa mở TikTok, nếu dính quảng cáo toàn màn hình hoặc popup lạ khiến `baseline["status"] != SUCCESS`, phải gọi `_swipe_recovery_on_stuck` trước khi check `manual_guard.record(_safety_from_row(ctx, baseline))`.
2. **Giai đoạn `before_swipe`:** Sau khi tap Home, nếu `before["status"] != SUCCESS` hoặc dính popup lạ chưa đóng được.
3. **Giai đoạn `swipe_after`:** Trong vòng lặp vuộn feed, nếu sau khi swipe dính quảng cáo/màn hình lạ không nhận diện được feed.

### 3. Pitfall cần tránh
- **Tránh xóa nhầm `baseline_stuck_recovery`:** Không đặt dòng kiểm tra `if manual_guard.record(...)` hay `if baseline["status"] != ExitStatus.SUCCESS.value: return finalize_feed_session_cleanup(...)` ở trước đoạn gọi `_swipe_recovery_on_stuck`.
