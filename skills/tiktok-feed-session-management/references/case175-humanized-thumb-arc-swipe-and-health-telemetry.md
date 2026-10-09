# Case 175: Vuốt Ngón Tay Sinh Học (Humanized Thumb Arc Swipe) & Quy Chuẩn Thiết Kế Telemetry Sức Khỏe Farm

## 1. Bối cảnh & Hiện trạng cũ (Before)
- **Vấn đề vuốt cơ học:** 
  - File `feed_swipe_smoke.py` trước đây cấu hình: `DEFAULT_SWIPE_DURATION_MIN_MS = 550`, `DEFAULT_SWIPE_DURATION_MAX_MS = 750`, `DEFAULT_SWIPE_DURATION_MS = 650`.
  - Tốc độ vuốt 550ms–750ms quá chậm và kéo lì (máy móc), không khớp với hành vi lướt feed thực tế của người dùng smartphone (ngón cái vuốt dứt khoát 200–400ms).
  - Tọa độ vuốt X bị giới hạn hẹp (`start_x [465, 525]`, `drift [-18, 12]`), và bẫy ẩn tại `_perform_feed_swipe`: `if abs(raw_end_x - start_x) > 30: end[0] = start_x` làm mọi cú vuốt có độ lệch tự nhiên >30px bị ép thẳng đứng cơ học.

## 2. Giải pháp kỹ thuật chuẩn hóa (Case Fix)
- **Anchor 1: Thời lượng vuốt dứt khoát sinh học:**
  - `DEFAULT_SWIPE_DURATION_MIN_MS = 240`
  - `DEFAULT_SWIPE_DURATION_MAX_MS = 400`
  - `DEFAULT_SWIPE_DURATION_MS = 330`
- **Anchor 2: Nới biên an toàn cho độ nghiêng ngón cái trong `_perform_feed_swipe`:**
  - Nâng điều kiện ép thẳng đứng từ `> 30px` lên `> 45px`.
  - Giữ hành lang an toàn `end_x`: `max(440, min(540, raw_end_x))` (cách mép trái >440px và cách cột action bar phải >360px).
- **Anchor 3: Quỹ đạo xoay khớp cổ tay (Thumb Arc Drift) trong `_build_swipe_parameters`:**
  - `start_x = max(470, min(525, BASE_SWIPE_START[0] + x_offset))` (vùng đặt tay người thuận tay phải).
  - `drift = 0 if jitter_px == 0 else random.randint(-35, 15)` (độ cong ngón cái nghiêng sang trái tự nhiên).
  - `end_x = max(440, min(540, start_x + drift))`.
  - `start_y = random.randint(1330, 1410)` và `end_y = random.randint(430, 510)` (quãng đường vuốt 820px–980px, luôn đảm bảo `start_y > end_y`).

## 3. Bài học thực chiến về Telemetry Sức Khỏe Farm (Anti-Overengineering)
- **Cảnh báo bẫy lý thuyết:** Chuyên gia AI / Reviewer lý thuyết (như Sol) thường đề xuất đo nhiệt độ CPU/pin, RAM throttling để tự động giảm tải farm.
- **Quy tắc thực tế:** Box farm có quạt tản nhiệt chạy 24/7, máy cày việc nặng nóng là bình thường. Tuyệt đối KHÔNG tự bóp limit, hạ quota hay hoãn ca chỉ vì máy nóng.
- **Chỉ số Telemetry thực chiến DUY NHẤT:**
  1. **View video đăng:** Đọc view từ lưới video Profile (phát hiện video 0-view sau 24h).
  2. **Follow nhả:** Đã có log từ `verify_follow.py`.
- **Hành động phản ứng:** Chỉ khi dính phạt 0-view liên tục hoặc follow bị nhả hàng loạt mới kích hoạt **Organic Rest 3 ngày (pure feed)** để giải trừ cờ phạt. Còn lại giữ nguyên công suất tối đa.
