# Invariant: Unconditional Dismiss for In-Feed Follow Suggestions & Friends Popups

## 1. Context & Root Cause
Trong các phiên bản cũ của `tiktok-luot nuoi acc`:
- `feed_swipe_smoke.py` (`follow_back_suggestion` blind popup rule): tự ý tap "Follow lại" / "Theo dõi lại" nếu tài khoản không dính cooldown.
- `benign_popup.py` (`dismiss_follow_friends_suggestion_popup`): tự ý tap follow 1-2 tài khoản trong popup "Gợi ý bạn bè / Follow bạn" trước khi đóng popup.

### Hậu quả thực tế trên farm:
1. **Follow mù không có post-verification:** Bấm nút follow trên UI nhưng không có cơ chế pull-to-refresh profile để kiểm tra xem server TikTok có thực nhận hay không. Khi bị TikTok silent-drop ngầm, script vẫn báo tăng dẫn đến watchdog đối soát với TikTok Web bị lệch âm (-2, -3).
2. **Kích hoạt follow bừa bãi trên máy không đủ điều kiện:** Các máy thuộc Farm Admin (máy 201-280) hoặc nick non (< 30 ngày, < 10 video) bị handler popup bấm follow dạo dù Dual Gate đang khóa cứng follow chéo.
3. **Làm cháy hạn mức Burst Velocity:** Thao tác follow dạo lúc lướt feed tiêu tốn quota hành vi của TikTok, khiến đến khi chạy follow chéo nội bộ thì tài khoản bị TikTok phạt nhả follow (action block).

---

## 2. Chuẩn Hóa Kiến Trúc: Tắt 100% Follow Tự Nhiên Khi Lướt Feed
**Quy tắc bất biến:**
- **Lướt feed (`tiktok-luot nuoi acc`):** Phục vụ 100% mục tiêu nuôi acc (lướt video, watch time, thả tim, comment peek, rewind, dọn dẹp popup). **TUYỆT ĐỐI CẤM BẤM NÚT FOLLOW DƯỚI MỌI HÌNH THỨC.**
- **Follow:** Độc quyền do `tiktok-follow` (`run_follow.py`) đảm nhiệm, với đầy đủ cơ chế Dual Gate, budget, ngâm video, và pull-to-refresh verify.

---

## 3. Quy Tắc Triển Khai Trong Code
1. **Thẻ Đề Xuất Follow Lại trên Feed (`feed_swipe_smoke.py`):**
   - Handler `follow_back_suggestion`: **LUÔN LUÔN** tìm và tap nút **"Không quan tâm"** (`//node[@text="Không quan tâm" or @content-desc="Không quan tâm" or @resource-id="com.ss.android.ugc.trill:id/cv6"]`).
   - CẤM phân nhánh tap "Follow lại" kể cả khi nick sạch.

2. **Popup Gợi Ý Bạn Bè / Gợi Ý Follow (`benign_popup.py`):**
   - Trong `dismiss_follow_friends_suggestion_popup`: đặt cứng `follow_limit = 0`.
   - Bỏ qua toàn bộ vòng lặp click nút Follow. Chỉ tìm nút đóng X, nút Back (`:id/bq7`), hoặc gửi phím Back để thoát popup sạch sẽ.

3. **Telemetry & Audit:**
   - Khi dismiss thẻ gợi ý follow, ghi log rõ `reason="unconditional_feed_suggestion_dismiss"` hoặc telemetry kèm trạng thái account để audit.
