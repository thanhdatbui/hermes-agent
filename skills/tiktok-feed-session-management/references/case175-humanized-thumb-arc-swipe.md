# Case 175: Humanized Thumb Arc Swipe with Natural Drift and Bio-Duration

## 1. Hiện Tượng & Động Lực Anti-Bot
- Trước Case 175, hàm lướt feed `_perform_feed_swipe` trong `feed_swipe_smoke.py` sử dụng:
  - Thời lượng kéo rê máy móc: `min_ms=550`, `max_ms=750`, `default=650ms`.
  - Quỹ đạo vuốt thẳng đứng cơ học: `start_x [465, 525]`, `drift = [-18, 12]`, bị clamp cứng `|dx| > 30px` ép thẳng đứng.
- Hệ quả: Hệ thống Anomaly Detection của TikTok dễ dàng phát hiện chữ ký robot cơ học (máy móc, kéo rê không tự nhiên, thiếu độ cong ngón cái của con người khi cầm điện thoại bằng một tay).

## 2. Giải Pháp Chuẩn Hóa (Thẩm định bởi Sol Web :20129)
- **Tốc độ vuốt dứt khoát (Biological Duration):**
  - Đưa dải thời lượng về chuẩn fling của người thật: `DEFAULT_SWIPE_DURATION_MIN_MS = 240`, `DEFAULT_SWIPE_DURATION_MAX_MS = 400`, `DEFAULT_SWIPE_DURATION_MS = 330`.
  - Giúp loại bỏ hoàn toàn hiện tượng kéo rê, phù hợp với màn hình cảm ứng Samsung Galaxy S7 Android 8.
- **Mô phỏng đường cong ngón cái (Thumb Arc Drift):**
  - Điểm đặt ngón tay `start_x`: Phân bổ tự nhiên vùng tay phải `[470, 525]` (cách xa mép trái và cột action rail bên phải).
  - Độ nghiêng vuốt tự nhiên khi xoay quanh khớp ngón cái: `drift = random.randint(-35, 15)`.
  - Nới biên an toàn lệch ngang: Nâng ngưỡng `|dx| > 30px` lên `|dx| > 45px` trong `_perform_feed_swipe`.
  - Hành lang kết thúc an toàn `end_x`: Clamp trong `[440, 540]` (cách mép màn hình >440px, cách nút Like/Comment >360px, không chạm nhầm UI).
  - Tọa độ trục Y: `start_y: 1330 – 1410` và `end_y: 430 – 510` (quãng đường vuốt `822px – 980px`, đảm bảo 100% kích hoạt chuyển trang video mượt mà).

## 3. Vị Trí Áp Dụng Codebase
- File: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`.
- Anchors can thiệp:
  1. Constants `DEFAULT_SWIPE_DURATION_*` (~L580-597).
  2. Nới ngưỡng skew và corridor an toàn trong `_perform_feed_swipe` (~L13349-13354).
  3. Tham số sinh ngẫu nhiên trong `_build_swipe_parameters` (~L13484-13489).

## 4. Verification & Kiểm Chứng
- `python -m py_compile "python_runner/flows/feed_swipe_smoke.py"`: PASS exit 0.
- Simulation test 1.000 mẫu ngẫu nhiên:
  - 100% mẫu có `240 <= duration <= 400`, trung bình `317ms`.
  - 100% mẫu có `start_y > end_y` và khoảng cách vuốt > 800px.
  - 100% mẫu tọa độ x nằm trong hành lang an toàn `[440, 540]`.
- Commit Git: `feat(feed-swipe): humanized thumb arc swipe with natural drift and bio-duration (Case 175)`.
