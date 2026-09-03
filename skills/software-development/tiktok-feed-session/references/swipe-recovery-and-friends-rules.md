# Swipe Recovery & Friends Flow Rules (22/08/2026)

## 1. Baseline Swipe Recovery
- **Bối cảnh:** Khi mở app TikTok ở bước `baseline`, nếu gặp video quảng cáo In-Feed Ad/TopView (như La Roche-Posay, v.v.) không có cụm nút tương tác chuẩn bên phải, `safety_check` / `classifier` sẽ trả về `status != success` hoặc `TikTok focus lost`.
- **Quy tắc:**
  - BẮT BUỘC gọi `_swipe_recovery_on_stuck` (thử vuốt 2 lần để lướt qua video lạ) TRƯỚC KHI `manual_guard` ngắt phiên.
  - Chỉ dừng lại ngay lập tức nếu `detected` thuộc các màn hình nhạy cảm thật:
    - `manual-needed:login`
    - `manual-needed:login-overlay`
    - `manual-needed:verification`
    - `manual-needed:captcha`
    - `manual-needed:security`
    - `manual-needed:manual_challenge`

## 2. Phân biệt Video Bạn bè vs Popup "Gợi ý Follow Bạn bè"
- **Video bạn bè bình thường (`friends` feed):**
  - Chiếm tỷ trọng phân bổ ~7% tổng thời lượng nuôi acc.
  - Vẫn xem (`watch_delay` 5s - 15s), thả tim (`like_rate` ~25%), và vuốt qua video tiếp theo bình thường.
- **Popup / Danh sách "Follow bạn bè của bạn" / "Follow lại":**
  - Nhận diện dạng modal danh sách gợi ý nhiều người dùng kèm nút "Follow lại".
  - Script sẽ bấm ngẫu nhiên tối đa 1 đến 2 nút "Follow lại", sau đó bấm chuyển tab về "Đề xuất" (hoặc nút X / phím Back) để khôi phục lại feed video chính.
