# Bài học Phục hồi Shadowban / Action Block TikTok & Khắc phục Lỗi 0-Like (2026-09-12)

## 1. Bản chất Kỹ thuật của Hiện tượng "Nhả Follow" (Silent Follow Drop)
- **Cơ chế:** Khi bị nghi ngờ bot/spam, TikTok áp dụng **Action Block: Silent Drop** trên server.
  - Trên màn hình máy: Bấm Follow -> App đổi tạm UI thành "Nhắn tin" (local optimistic UI).
  - Trên server TikTok: Request follow bị hủy bỏ âm thầm.
  - Khi thoát app mở lại hoặc vuốt reload: Nút chuyển lại về màu đỏ `Follow`.
- **Sliding Window & Decay Factor (Khẳng định từ Claude Opus):**
  - Hệ thống Anti-Abuse (Isolation Forest / GNN) tính điểm theo cửa sổ trượt 14–21 ngày.
  - Tỷ lệ `In-feed engagement (Like/Save)` vs `Outbound action (Follow)` là **chữ ký bất biến có trọng số cực cao**.
  - Khi một farm mất tín hiệu Like trong khi vẫn tiếp tục Follow -> Tài khoản rơi vào anomaly cluster -> Sau 2–3 tuần điểm Trust phân rã dưới ngưỡng -> Bị trảm đồng loạt cả cụm.

## 2. Tử huyệt 0-Like suốt 26 ngày (18/08 -> 12/09/2026)
- **Nguyên nhân:** Đêm 17/08, TikTok gộp node `ImageView` (`content-desc="Thích"`) thành 1 node `Button` duy nhất mang text động: `content-desc="Thích video. 41,3K lượt thích"`.
- **Hậu quả:** Code so sánh cứng `content_desc == "Thích"` bị mù 100%, 80 máy chạy 4 ca/ngày suốt 26 ngày không thả tim nổi 1 video -> Trust Score sụp về 0 -> 90% farm dính cờ nhả follow.
- **Khắc phục:**
  - So khớp tiền tố case-insensitive: `desc.lower().startswith("thích video")` hoặc `desc.lower().startswith("like video")`.
  - Lấy clickable qua attrib: `element.attrib.get("clickable") == "true"`.
  - Loại trừ header tab: `element.center[1] >= 350`.
  - Bổ sung đếm `like_counts` vào báo cáo Telegram Watchdog (`feed_session_watchdog.py`).

## 3. Quy chuẩn Nuôi phục hồi và Giới hạn Thời gian
- **Tăng thể tích video:** Nâng từ 8–11 video lên **16–22 video (max 28 swipes)**.
- **Tính toán Timeout thực tế trên phần cứng:**
  - Lướt feed thực tế có độ trễ dump XML, popup, settling delay: ~14–16 phút cho 8–11 video.
  - Khi nâng lên 16–22 video, thời gian chạy thực tế kéo dài lên **28–35 phút/máy**.
  - **Bắt buộc nâng `DEFAULT_DEVICE_TIMEOUT_SECONDS` từ 2100s (35p) lên 3000s (50p)** để tránh bị timeout sập luồng.
- **Bác bỏ Trick "Chuyển nick ngâm qua đêm":**
  - Backend TikTok chỉ tính telemetry có traffic thật. Máy tắt màn hình ngủ 7 tiếng không có traffic = vô hình = 0 điểm Trust.
  - Switch trước qua đêm còn tiềm ẩn rủi ro Stale Token và lệch Network Context (khi IP mạng/proxy xoay trong đêm).
  - Quy chuẩn đúng: Đến giờ ca nào -> Mở máy kiểm tra IP -> Switch đúng nick -> Lướt feed 15 phút (có like) -> Mới follow/upload.

## 4. Tinh hoa từ Flow GemPhoneFarm (Anh Khoa)
- **Ad Fast-Skip (Bỏ qua quảng cáo):** Gặp `//node[@text="Được tài trợ"]` -> vuốt qua ngay lập tức trong <1s, không dừng xem và không like.
- **Pre-like Watch Time:** Khi trúng tỷ lệ like, dừng xem 4.5s – 15s trước khi tap, tap xong dừng 1.5s – 3s mới vuốt tiếp.
- **Đóng thanh trượt CAPTCHA:** Tap `//node[@resource-id="verify-bar-close"]` đóng nhanh popup thử thách.
