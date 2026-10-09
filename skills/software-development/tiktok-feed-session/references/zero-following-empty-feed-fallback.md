# Xử lý Tab Following cho Nick 0-Following & Cơ chế Auto-Fallback về FYP

## 1. Hiện tượng & Bản chất sự cố
- Khi chạy kịch bản nuôi nick / lướt feed (`tiktok-luot nuoi acc`), theo quy luật tự nhiên bot phân bổ tỷ lệ chuyển tab:
  * 70% tab "Dành cho bạn" (For You / FYP)
  * 15% tab "Đang follow" (Following)
  * 15% tab "Bạn bè" (Friends)
- Đối với các **tài khoản mới đăng ký (0-following)** hoặc tài khoản chưa có kênh follow nào đăng video mới:
  * Khi bot tap chuyển sang tab "Đang follow", server TikTok không có video để nạp nên trả về màn hình rỗng kèm thông báo mặc định của app:
    > `Đã xảy ra lỗi | Vui lòng thử lại. | [Thử lại]`
  * Nếu classifier hoặc luồng xác nhận chuyển tab (`switch_{next_feed_type}_{swipe_count}_navigation_confirm`) thấy nút `Thử lại` và phân loại thành `manual-needed:network`, script sẽ hiểu lầm là thiết bị bị rớt mạng / sập proxy.
  * Hậu quả: `manual_guard.record()` ngắt ngang toàn bộ phiên lướt feed, đánh dấu fail phiên dù mạng và proxy của máy vẫn sống 100% và vừa lướt hàng chục video FYP mượt mà trước đó.

## 2. Chỉ thị thiết kế chuẩn của User (User Invariant 2026-09-24)
- **CẤM bỏ qua việc vào tab Following:** Không được hardcode chặn vào tab Following ngay từ đầu (bằng cách ép rate = 0) vì việc bấm vào tab Following là một phần của hành vi mô phỏng người dùng tự nhiên khi nuôi nick.
- **CƠ CHẾ AUTO-FALLBACK:** Bot vẫn bấm vào tab Following bình thường. Nhưng khi vừa vào đó, nếu phát hiện màn hình rỗng hoặc lỗi mạng ảo của tab (`"manual-needed:network"`, `"manual-needed:empty"`, `"manual-needed:retry"` do nick chưa follow ai):
  1. **Tuyệt đối KHÔNG dừng phiên**, không ghi nhận fail mạng toàn app.
  2. Ghi log cảnh báo `warning`:
     ```python
     ctx.logger.log(
         device_id=ctx.device_id,
         account=ctx.account,
         step=f"{artifact_prefix}/switch_{next_feed_type}_{swipe_count}_empty_feed_fallback_for_you",
         action="fallback_feed_tab",
         result="warning",
         extra={"failed_target": next_feed_type, "fallback_target": FEED_TYPE_FOR_YOU, "reason": "empty_following_or_network_marker_fallback_to_for_you"},
     )
     ```
  3. Lập tức **tap quay ngược lại tab "Dành cho bạn" (For You)**:
     ```python
     tap_navigation_target(
         ctx,
         _top_tab_target(FEED_TYPE_FOR_YOU),
         current_top_tab=next_feed_type,
         artifact_prefix=artifact_prefix,
         log_prefix=artifact_prefix,
     )
     ```
  4. Cập nhật `current_feed_type = FEED_TYPE_FOR_YOU`, `confirm["status"] = ExitStatus.DEGRADED.value`, `confirm["safety_status"] = "ok"`.
  5. Thiết lập `videos_until_tab_decision = random.randint(5, 10)` và tiếp tục lướt các video trên tab For You cho đến khi hoàn thành đủ 100% quota video của ca chạy.

## 3. Khóa chống nhận diện nhầm Profile người lạ thành Home Feed
- Khi bot lướt feed gặp pop-up gợi ý bạn bè hoặc lỡ bấm vào profile công khai của người lạ, trên trang này có thể có nút `"Đã follow"` hoặc `"Đang follow"`.
- Trong `calibrate_screens.py` và `classifier.py`:
  * Nếu phát hiện các nút hành động của profile người khác (`"Follow lại"`, `"Nhắn tin"`, `"Follow back"`, `"Message"`): BẮT BUỘC đánh dấu `is_foreign_profile = True`.
  * Khi `is_foreign_profile = True`, **CẤM TUYỆT ĐỐI** xem màn hình đó là `is_home_or_feed` và cấm chặn lệnh `KEYCODE_BACK`.
  * Phải cho phép gửi chuỗi `KEYCODE_BACK` để bot tự động lùi về Home Feed chính.
