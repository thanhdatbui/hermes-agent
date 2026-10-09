# Case 85: Camera Surface Visual Upload Entry Precedence (L/BL over R)

## Bối cảnh & Triệu chứng
- **Triệu chứng:** Khi chạy upload trên máy Samsung (hoặc các thiết bị camera-first), quy trình kẹt tại `VIDEO_PICK` và fail với `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Trong hàm `_tap_visual_camera_upload_entry(adapter)`, các toạ độ ứng viên visual được phát hiện dựa trên `non_dark` pixels:
    - `R` (Right): `(width * 0.875, height * 0.83)`
    - `L` (Left): `(width * 0.145, height * 0.82)`
    - `BL` (Bottom-Left): `(width * 0.11, height * 0.95)`
  - Trước đây, `valid_targets` append `R` đầu tiên nếu `non_dark_r >= 0.20`. Trên nhiều giao diện TikTok mới, góc phải (`R`) là nút **Mẫu / CapCut Template** (hoặc Hiệu ứng), có `non_dark_r ~ 0.45` nên luôn được ưu tiên tap trước.
  - Khi tap `R`, TikTok mở màn hình Template preview / hub thay vì mở gallery picker.
  - Sau khi gọi `_dismiss_capcut_template_surface`, thao tác back làm TikTok thoát hẳn khỏi màn hình Camera và rơi về Feed (`not self._is_camera_surface_xml`), dẫn đến hàm trả về `False`.
  - Luồng ngoài tiếp tục retry bằng cách nhấn lại `+` để vào camera, rồi lại gọi `_tap_visual_camera_upload_entry` và lặp lại việc tap vào `R`. Cuối cùng kiệt retry và fail `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
  - Trong khi đó, ô thumbnail Thư viện album ảnh thực sự nằm ở bên trái (`L` hoặc `BL`) với độ sáng rõ nét (`non_dark_l ~ 0.95`).

## Quy tắc xử lý chuẩn (Standard Rule)
1. **Ưu tiên Left (`L` / `BL`) trước Right (`R`):**
   - Luôn kiểm tra và sắp xếp các target bên trái (`L`, `BL`) lên đầu danh sách `valid_targets`.
   - Có thể sắp xếp `L` và `BL` theo điểm `non_dark` giảm dần (score cao hơn được tap trước).
   - `R` chỉ được dùng làm fallback cuối cùng nếu không có target bên trái nào thỏa mãn `non_dark >= 0.20`.
2. **Xử lý chống văng về Feed khi dismiss Template:**
   - Nếu vô tình rơi vào template surface và dismiss khiến màn hình rơi về Feed (có nút `+`), caller hoặc hàm visual recovery cần kiểm tra `_find_bounded_create_button` để tap lại vào Camera thay vì lập tức fail-closed.
3. **Đồng bộ Unit Tests:**
   - Cập nhật các test case liên quan đến visual upload thumbnail trong `tests/test_tiktok_workflow.py` (`test_tap_visual_camera_upload_entry_stops_if_camera_lost_after_dismiss_template`, `test_video_pick_camera_thumbnail_alternates_retry_targets`) để phản ánh đúng thứ tự ưu tiên `L` -> `R`.
