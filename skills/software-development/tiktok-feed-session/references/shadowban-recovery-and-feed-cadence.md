# KIẾN THỨC VẬN HÀNH & PHỤC HỒI SHADOWBAN FOLLOW (CASE TIK1/TIK2 12/09/2026)

## 1. Bản chất Shadowban Action Block trên TikTok
- **Không có chuyện "ngọng vĩnh viễn"**: TikTok không bao giờ khóa cứng nút follow vĩnh viễn của tài khoản bình thường. Nó chỉ áp dụng **Temporary Action Block (Silent Drop)**:
  - Khi tap nút Follow trên video hoặc profile, app local vẫn render trạng thái "Nhắn tin" / "Following".
  - Nhưng request bay lên server bị drop âm thầm.
  - Ngay khi thoát app ra vào lại hoặc reload, nút lập tức nhảy ngược lại về màu đỏ `Follow` (bằng chứng thực nghiệm 100% trên Máy 24 ngày 12/09/2026).
- **Nguyên nhân 0 acc tự phục hồi khi ngâm cooldown thuần túy**:
  - Dữ liệu 144 file follow_state: 127 nick dính cờ nhả follow, 0 nick tự phục hồi nếu chỉ ngâm ngày chờ hết cooldown.
  - Lý do: Thuật toán TikTok không tự ân xá cho tài khoản "chết lâm sàng" (chỉ nằm im hoặc lướt feed zombie 0 likes). Điểm Trust Score vẫn ở mức 0.

## 2. Công thức Phục hồi (Đã được kiểm chứng & Anh Khoa Lee xác nhận)
- **"Nuôi đăng video đều là follow được e"**:
  1. **Upload Video đều đặn**: Tín hiệu hồi sinh Trust Score mạnh nhất. Hệ thống 48h đăng 1 video (1 nick 2 ngày 1 lần) là tần suất cực chuẩn của user thật, không bị quét upload spam và không cạn kho video.
  2. **Thứ tự thực thi trong 1 phiên**:
     - Mở app -> **LƯỚT FEED TRƯỚC** (16-22 video, 15-20 phút, có thả tim thật) -> **SAU ĐÓ MỚI GỌI UPLOAD HOOK ĐĂNG VIDEO**.
     - Đăng xong -> Xem nhẹ profile 5-10s -> Thoát app.
  3. **Lướt Feed có Thả tim thật (Đã fix selector prefix match)**:
     - Selector Like trên TikTok chứa counter: `content-desc="Thích video. 41,3K lượt thích"`. Tuyệt đối không so sánh bằng tuyệt đối `== "Thích"`.
     - Phải dùng prefix match: `desc_lower.startswith("thích video")` hoặc `desc_lower.startswith("like video")`.
     - Fast Swipe (2-4s) cho tab For You, Deep Inspect (4-15s, dump XML, like rate bù trừ 40%) cho video xem chậm và 100% tab Following/Friends.

## 3. Tần suất & Thông số nuôi chuẩn sau nâng cấp
- `FEED_SESSION_MIN_TOTAL_VIDEOS = 16`
- `FEED_SESSION_MAX_TOTAL_VIDEOS = 22`
- `FEED_SESSION_MAX_SWIPES = 28`
- Phân bổ tab: For You 70% (Like bù trừ 40% ở deep inspect ~ 10-12% toàn phiên), Following 15% (Like 30%), Friends 15% (Like 70%).
- Thời lượng cả phiên: 16 - 20 phút / máy (an toàn dưới timeout 35 phút = 2100s).
