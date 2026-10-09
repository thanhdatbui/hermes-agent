# BỔ SUNG QUY TRÌNH HỒI PHỤC NICK SHADOWBAN & AD FAST-SKIP (2026-09-12)

## 1. Bản vá Lỗi 0 Like & Giám sát Watchdog
- TikTok thay đổi UI từ 18/08/2026, gộp `ImageView` có `content-desc="Thích"` vào button lớn `content-desc="Thích video. 41,3K lượt thích"`.
- Đã sửa hàm nhận diện Like dùng tiền tố `desc.lower().startswith("thích video")` hoặc `"like video"` hoặc `txt.lower().startswith("thích")`.
- Loại trừ tab navigation ở đỉnh màn hình: `center[1] < 350`.
- Đã thêm tổng số lượt thả tim vào báo cáo Telegram Watchdog (`feed_session_watchdog.py`) để kiểm soát không bị 0 Like âm thầm.

## 2. Nâng cấp Thể tích Feed & Timeout
- `FEED_SESSION_MIN_TOTAL_VIDEOS = 16`
- `FEED_SESSION_MAX_TOTAL_VIDEOS = 22`
- `FEED_SESSION_MAX_SWIPES = 28`
- `DEFAULT_DEVICE_TIMEOUT_SECONDS = 3000.0` (50 phút): Thời gian lướt 16-22 video thực tế mất ~28-35 phút do độ trễ dump XML và delay xem. Phải để timeout 50 phút mới an toàn tuyệt đối, tránh văng timeout.

## 3. Cơ chế Ad Fast-Skip (học từ script GemPhoneFarm anh Khoa)
- Trong `feed_swipe_smoke.py`, hàm `_is_sponsored_xml`:
  - Dùng `iter_elements` quét toàn bộ cây XML.
  - Quét `text` và `content_desc` không phân biệt hoa thường với `SPONSORED_TEXTS = ("Được tài trợ", "Sponsored")`.
  - Khi phát hiện quảng cáo: ghi log `skip_sponsored`, quẹt lướt bỏ qua ngay lập tức trong 0.5s, không tính thời gian xem lâu và không bấm thả tim vào video quảng cáo.

## 4. Cơ chế Post-Cooldown Warmup (Repo `tiktok-follow`)
- Trong `follow_state.py`: Tài khoản vừa hết hạn cooldown (`fail_streak > 0` và `follow_failed == False`) được đánh dấu `is_post_cooldown_warmup = True`.
- Hạ `session_budget` xuống mức thăm dò: **3 – 5 follow / phiên** (thay vì 6–10 follow).
- Follow 3–5 nick thành công $\rightarrow$ gọi `reset_follow_failed()` tự động xóa `fail_streak = 0`, phục hồi tài khoản về bình thường.

## 5. Bác bỏ kỹ thuật: "Switch tài khoản trước rồi ngâm qua đêm"
- Server TikTok backend chỉ tồn tại thông qua telemetry. Thiết bị idle tắt màn hình 7 tiếng không có traffic = vô hình với backend, không hề được cộng Trust Score.
- Sáng mở máy vẫn là Cold Start, Play Integrity token chỉ có hiệu lực vài phút nên vẫn phải fetch lại từ đầu.
- Rủi ro lớn nhất: Nếu IP nhà mạng tự đổi hoặc proxy reconnect trong đêm $\rightarrow$ phiên tạo ở IP cũ nhưng dùng ở IP mới gây **Lệch Network Context (Network Mismatch)**, dễ dính cờ bot hơn.
- Quy trình chuẩn: Đến đúng giờ ca chạy mới mở app $\rightarrow$ check mạng $\rightarrow$ switch nick $\rightarrow$ lướt feed 15-25 phút $\rightarrow$ mới follow / upload.
