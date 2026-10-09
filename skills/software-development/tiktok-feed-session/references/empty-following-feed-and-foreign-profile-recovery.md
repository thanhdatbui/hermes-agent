# Empty Following Feed False Positive & Foreign Profile Escape Recovery

## 1. Empty Following Feed False Positive Network Error (Bẫy Lỗi Mạng Khi 0 Following)

### Triệu chứng
- Máy nuôi đang lướt Feed bình thường (đã lướt 3-18 video trên FYP) thì đột ngột dừng với mã lỗi:
  `stop_reason: network/error/retry marker detected`
  hoặc `status: manual-needed:network` tại step `switch_following_<N>_navigation_confirm`.
- Tỷ lệ fail dồn theo lô các nick mới reg hoặc nick dưỡng sinh.

### Phân tích hiện trường & Nguyên nhân gốc rễ
- **Proxy và Wi-Fi hoàn toàn bình thường:** Bằng chứng là các video FYP trước đó đã lướt mượt mà, lượt view và tim tăng đều.
- **Hiện tượng 0 Following:** Khi kiểm tra Profile cá nhân của nick, số lượng `Đã follow` = 0 (tài khoản mới chưa follow ai, hoặc các nick được follow chưa từng đăng video).
- **Màn hình rỗng của TikTok:** Khi bot chuyển tab từ "Dành cho bạn" (FYP) sang tab "Đang Follow" (Following), TikTok không có nội dung để hiển thị nên render màn hình rỗng với thông báo lỗi mặc định:
  `Đã xảy ra lỗi | Vui lòng thử lại. | [Thử lại]` (hoặc `Something went wrong. Tap to retry`).
- **Classifier Match Nhầm:** `classifier.py` quét thấy cụm từ `"Thử lại"` / `"Retry"` liền phân loại thành `manual-needed:network`, ngắt toàn bộ phiên nuôi sớm và tính là máy lỗi.

### Quy tắc xử lý & Invariant
1. **Kiểm tra số lượng Following tại Preflight:**
   - Khi preflight đọc hồ sơ (`read_profile_identity`), nếu ghi nhận `following == 0` (hoặc < 2 người):
   - Tự động gán trọng số phân bổ tab Following về 0 (`feed_distribution[FEED_TYPE_FOLLOWING] = 0.0`), dồn 100% thời lượng cho tab "Dành cho bạn" (FYP) và "Bạn bè". Tránh việc bấm sang tab Following chỉ để nhận thông báo rỗng.
2. **Cơ chế xác thực đối chứng (Cross-Tab Verification):**
   - Tuyệt đối không kết luận thiết bị rớt mạng chỉ dựa vào thông báo "Thử lại" trên tab Following.
   - Nếu tab Following báo lỗi, thử quay lại tab FYP. Nếu FYP vẫn tải được video bình thường thì kết luận đây là **Empty Following Feed**, tiếp tục phiên nuôi trên FYP và ghi nhận degraded thay vì fail closed.

---

## 2. Bẫy Kẹt Profile Người Khác & Bị Bỏ Qua KEYCODE_BACK

### Triệu chứng
- Máy dừng với lỗi `navigation target profile not found in XML` ngay từ bước đầu (0 swipes completed).
- Hiện trường ảnh chụp cho thấy màn hình đang mở trang cá nhân của một người dùng TikTok khác (có nút "Follow lại", "Nhắn tin").

### Nguyên nhân gốc rễ
1. **Chuyển hướng ngoài ý muốn:** Khi mở app, TikTok hiển thị popup "Gợi ý kết bạn" / "Follow lại" hoặc suggestion card trên feed. Khi popup bị bấm trúng, TikTok nhảy vào trang Profile của người lạ.
2. **Thanh điều hướng đáy biến mất:** Ở trang profile người khác, thanh tab dưới cùng không có nút "Hồ sơ" của mình -> `find_navigation_target` không tìm thấy target.
3. **Bẫy `is_home_or_feed` trong `calibrate_screens.py`:**
   - Trong `calibrate_screens.py`, logic kiểm tra an toàn trước khi bấm `KEYCODE_BACK` có đoạn:
     ```python
     if any(current_markers.get(k) for k in ("home_selected", "for_you_selected", "following_selected", ...)):
         is_home_or_feed = True
     ```
   - Trang profile người lạ hiển thị thống kê tài khoản có nhãn `"Đã follow"` (ví dụ: `210 Đã follow | Follower | Thích`).
   - `"Đã follow"` nằm trong danh sách `following_terms` của classifier -> script nhận diện nhầm đây là Tab Following của Home Feed -> gán `is_home_or_feed = True` -> log `navigation_back_recovery_skipped_at_home_feed` và **CẤM bấm phím BACK**!
   - Kết quả: Máy kẹt vĩnh viễn ở profile người lạ cho đến khi hết timeout.

### Quy tắc xử lý & Invariant
1. **Loại trừ nhãn thống kê khỏi tab Following:**
   - `following_terms` trong bộ nhận diện tab chỉ chứa các từ đại diện cho Tab Header (`"Following"`, `"Đang Follow"`), không dùng chuỗi đa nghĩa `"Đã follow"` vốn xuất hiện trên mọi profile.
2. **Nhận diện Public Profile người lạ (`is_foreign_profile`):**
   - Nếu màn hình chứa các nút hành động đặc trưng của người khác: `"Follow lại"`, `"Nhắn tin"`, `"Follow back"`, `"Message"`.
   - Bắt buộc xác định `is_home_or_feed = False`, cho phép thực thi chuỗi `KEYCODE_BACK` (tối đa 2 lần) để app thoát khỏi profile người lạ và trở về Home Feed an toàn.

---

## 3. Runtime Tab Fallback Về For You (FYP) Khi Kẹt Empty / Network Marker (2026-09-23)

### Bối cảnh Vận hành Batch
- Trong ca nuôi (Ca 2/Ca 3), hàng loạt máy dính cảnh báo `network/error/retry marker detected` (ví dụ M33, M41, M70, M72, M75) khi runner chuyển tab sang Following/Friends.
- Bản chất không phải rớt mạng internet hay proxy hỏng mà do tài khoản mới hoặc ít following khiến tab Following/Friends rỗng, TikTok hiển thị thông báo lỗi mạng giả lập ("Chưa có video nào" / "Chạm để thử lại").
- Nếu `manual_guard.record()` ngắt ngay lập tức, toàn bộ máy bị hủy phiên oan uổng và lãng phí thời gian nuôi.

### Contract Tự Phục Hồi Tại `feed_swipe_smoke.py` (`_feed_session_flow`)
```python
if next_feed_type in {FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS} and confirm.get("detected") in {"manual-needed:network", "manual-needed:empty", "manual-needed:retry"}:
    ctx.logger.log(
        device_id=ctx.device_id,
        account=ctx.account,
        step=f"{artifact_prefix}/switch_{next_feed_type}_{swipe_count}_empty_feed_fallback_for_you",
        action="fallback_feed_tab",
        result="warning",
        extra={"failed_target": next_feed_type, "fallback_target": FEED_TYPE_FOR_YOU, "reason": "empty_following_or_network_marker_fallback_to_for_you"},
    )
    # Graceful fallback: Tap back to For You feed and continue session quota
    tap_navigation_target(
        ctx,
        _top_tab_target(FEED_TYPE_FOR_YOU),
        current_top_tab=next_feed_type,
        artifact_prefix=artifact_prefix,
        log_prefix=artifact_prefix,
    )
    current_feed_type = FEED_TYPE_FOR_YOU
    next_feed_type = FEED_TYPE_FOR_YOU
    confirm["status"] = ExitStatus.DEGRADED.value
    confirm["safety_status"] = "ok"
    videos_until_tab_decision = random.randint(5, 10)
```
- **Hành vi:** Đưa app quay trở lại FYP an toàn, hạ trạng thái xuống `DEGRADED`, reset nhịp quyết định đổi tab kế tiếp (5-10 video) và tiếp tục lướt feed hoàn thành chỉ tiêu tổng số video.
- **Hiệu quả:** Xóa bỏ hoàn toàn các ca fail-closed giả mạo do rỗng tab Following trên toàn dàn 80-160 máy.

