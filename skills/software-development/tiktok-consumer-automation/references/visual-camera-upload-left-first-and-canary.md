# Visual Camera Upload Entry: Left-First Thumbnail Strategy & Test Alignment

## Context & Root Cause
Trong luồng upload TikTok trên một số thiết bị Samsung (ví dụ máy 39), khi camera mở không có node upload XML trực tiếp, hệ thống dùng phân tích hình ảnh (visual check) để tap thumbnail đưa vào gallery picker.
Trước đây, thứ tự target ưu tiên góc Phải (`R` ~ `(945, 1593)`), sau đó mới tới Trái (`L` / `BL`).
Tuy nhiên, tap vào Right thumbnail trên nhiều layout/phiên bản TikTok hiện tại dễ trigger template CapCut ("Thử mẫu này") hoặc nút tạo hiệu ứng thay vì mở gallery chọn video.

## Chi Tiết Kỹ Thuật

### 1. Thứ Tự Ưu Tiên Thumbnail (Left-First)
- **Cấu hình thứ tự**: Ưu tiên toàn bộ các ứng viên Left (`L`, `BL`) trước Right (`R`).
  ```python
  left_targets.sort(key=lambda item: item[2], reverse=True)
  ordered_candidates = left_targets + right_targets
  ```
- **Xử lý Template rơi về Feed**:
  Nếu dismiss CapCut template khiến màn hình rơi về Home/Feed thay vì giữ lại camera surface, kiểm tra và tap lại nút Create (`+`) để tái lập camera surface trước khi thử target tiếp theo.

### 2. Quy Tắc Đồng Bộ Unit Test (`tests/test_tiktok_workflow.py`)
Khi thay đổi thứ tự ưu tiên sang Left-first:
- **`test_tap_visual_camera_upload_entry_stops_if_camera_lost_after_dismiss_template`**:
  Initial tap sẽ là Left (`(156, 1574)`). Khi template xuất hiện và bị dismiss rồi camera bị mất, workflow phải dừng lại và KHÔNG được tap alternative Right thumbnail:
  ```python
  assert (945, 1593) not in adapter.taps
  ```
- **`test_video_pick_camera_thumbnail_alternates_retry_targets`**:
  Sequence luân phiên các lượt tap retry phải bắt đầu từ Left:
  ```python
  assert adapter.taps == [(118, 1824), (945, 1593), (118, 1824)]
  ```

### 3. Canary Test & Timeout Gate
- Các canary test live device (`--no-dry-run`) đi qua 20 state (từ `INIT`, `CONNECT_DEVICE`, `ACCOUNT_READY`, `MEDIA_PUSH`, tới `VIDEO_PICK` và post/verify) có thể tốn từ 3–7 phút tùy độ trễ thiết bị thực và media scan.
- Đảm bảo timeout cho lệnh terminal tối thiểu 600s hoặc chạy background có notification để tránh bị ngắt quãng giữa chừng khi máy đang xử lý gallery/picker.
