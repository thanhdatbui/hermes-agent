# TikTok Rewards & Age Verification (18+) Modal Handling

## 1. Hiện tượng & Cơ chế phát sinh (Diagnostic)
- **Bối cảnh:** Trong quá trình chạy `multi-machine-feed-session` hoặc `feed_swipe_smoke` lướt For You feed, TikTok thường hiển thị widget nổi (floating badge) hoặc banner chiến dịch **"Phần thưởng TikTok"** (TikTok Rewards).
- **Cơ chế:** Thao tác vuốt/chạm trên Feed vô tình chạm vào widget hoặc TikTok tự chuyển hướng mở WebView sự kiện tích điểm thưởng.
- **Biểu hiện UI:**
  - Tiêu đề WebView: *"Phần thưởng TikTok"* (hoặc điểm thưởng nhiệm vụ xem phim/video).
  - Modal Pop-up chặn giữa màn hình: *"Bạn phải đủ 18 tuổi trở lên để tiếp tục"* (You must be 18 years or older to continue).
  - Nội dung: *"Khi nhấn vào "Đồng ý" bên dưới, bạn xác nhận rằng bạn đủ 18 tuổi trở lên..."* kèm link *"Điều khoản và điều kiện >"*.
  - 2 nút điều khiển: Bên trái là **"Hủy"**, bên phải là **"Đồng ý"**.
- **Hậu quả nếu chưa đăng ký handler:** Bộ kiểm tra an toàn `safety_check` xác định trạng thái UI là `unknown TikTok state` -> Dừng phiên lập tức (ExitStatus.MANUAL_NEEDED) -> Chụp ảnh màn hình đính banner đỏ `[MAY X] - HH:MM:SS dd/mm` và gửi cảnh báo Telegram giữ nguyên hiện trường.

---

## 2. Quy trình xử lý & Thoát an toàn (Dismiss Contract)
1. **Xử lý trên máy hiện trường:**
   - Ưu tiên bấm **"Hủy"** hoặc gửi phím `BACK` (`send_device_back_key(ctx)` / `input keyevent 4`) để đóng modal 18+ mà không xác nhận điều khoản sự kiện.
   - Gửi tiếp 1 phím `BACK` để đóng trang WebView *Phần thưởng TikTok*, đưa máy trở lại màn hình chính For You feed.

2. **Quy tắc thêm vào `BENIGN_POPUP_REGISTRY` & `GEMPHONEFARM_BLIND_POPUP_RULES`:**
   - **Detector Markers:**
     - Tiếng Việt: `"Bạn phải đủ 18 tuổi trở lên"`, `"18 tuổi trở lên để tiếp tục"`, `"Phần thưởng TikTok"`, `"Điều khoản và điều kiện của sự kiện này"`.
     - Tiếng Anh: `"18 years or older"`, `"TikTok Rewards"`.
   - **Dismiss Action:**
     - Tap nút `"Hủy"` (hoặc phím BACK lần 1).
     - **Quan trọng:** Kiểm tra lại hierarchy sau tap/BACK lần 1 — CHỈ gửi BACK lần 2 nếu phát hiện trang sự kiện/modal vẫn còn hiển thị (`_detect_tiktok_rewards_terms(xml_after)`). Tuyệt đối không gửi mù BACK lần 2 vì nếu modal đã đóng và app đã tự về Feed thì phím BACK thừa sẽ làm thoát Feed hoặc đóng TikTok app.
     - **Test coverage requirement:** Khi viết unit test cho dismisser dạng này, cần mock `elem.bounds` dưới dạng tuple/list `(100, 500, 300, 600)` tương thích với `UIElement` parse từ `automation_core.ui` và kiểm tra cả trường hợp tap nút Cancel lẫn thoát an toàn.
