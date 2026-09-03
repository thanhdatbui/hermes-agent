# Camera Upload Thumbnail Visual Gate & Bounded Tap Recovery (VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED)

## Triệu chứng lỗi (Incident Pattern)
- **State:** `VIDEO_PICK`
- **Error:** `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery` / `upload_subprocess_nonzero`
- **Log marker:** `Camera upload thumbnail visual gate rejected screenshot` hoặc `Camera upload thumbnail tap did not open a verified gallery picker`.
- **Hiện trường:** Sau khi bấm nút Tạo (+), TikTok mở giao diện Camera. Nút "Tải lên" ở góc dưới bên phải shutter có hình thu nhỏ (thumbnail) của video trong máy nhưng có viền bo tròn hoặc nội dung video gam màu tối/ban đêm.

## Root Cause
1. **Ngưỡng Visual Gate quá cao (0.45):**
   Hàm `_tap_visual_camera_upload_entry` cắt vùng thumbnail `(0.81w, 0.77h) -> (0.94w, 0.87h)` và tính tỷ lệ pixel sáng `non_dark = sum(max(r,g,b) > 35) / len(pixels)`. Với các thumbnail tối hoặc viền đen, tỷ lệ `non_dark` thực tế chỉ đạt ~0.25 - 0.35 (máy 38 đạt 0.3007). Ngưỡng cũ `>= 0.45` từ chối nhầm thumbnail hợp lệ.
2. **Layout thumbnail đa dạng (góc phải vs góc trái):**
   Trên một số phiên bản Samsung hoặc giao diện camera-first, nút Tải lên/thumbnail có thể nằm ở góc dưới bên trái (`upload_hot_area` / `view_bg2` tại `[60,1761][180,1881]`) thay vì góc phải shutter. Nếu visual gate chỉ scan góc phải thì sẽ bị từ chối hoặc tap hụt.
3. **Bỏ sót selector XML khi đã ở Camera surface:**
   XML dump của Camera surface có thể đã hiển thị node thumbnail (`view_bg2`, `upload_hot_area`...). Nếu không ưu tiên tap XML mà nhảy thẳng vào visual coordinate, script dễ tap lệch. Đồng thời, nếu tap XML làm UI chuyển sang màn hình khác không phải gallery (như dialog permission), cần fail-closed ngay thay vì tiếp tục tap mù trên XML cũ.

## Giải pháp chuẩn (Standard Fix)
1. **Ưu tiên XML Selector trên Camera:**
   Quét và tap trực tiếp qua các selector XML (`view_bg2`, `upload_hot_area`, `cwr`, `upload_work`, "Tải lên", "Upload"). Sau mỗi tap XML, nếu UI rời Camera mà không mở được picker thì abort fail-closed ngay để tránh tap sai.
2. **Dual Visual Gate & Alternating Retry:**
   - Quét cả thumbnail góc phải (`[0.81..0.94, 0.77..0.87]`) và thumbnail góc trái (`[0.05..0.18, 0.90..0.99]`) với ngưỡng `non_dark >= 0.20`.
   - Chỉ thu thập các target đạt visual gate và luân phiên retry (tối đa 4 lần) giữa các valid targets khi UI vẫn còn ở trạng thái `_is_camera_surface_xml`.
3. **Fallback Bounded Create Button trên Feed:**
   Trong `_handle_video_pick`, nếu các resource-id dấu + chuẩn bị obfuscate/thiếu thì fallback sang `_find_bounded_create_button` trước khi gọi visual create button để tap đúng nút Tạo (+) ở trung tâm đáy màn hình.
4. **Cập nhật Unit Tests:**
   Thêm các test:
   - `test_video_pick_camera_thumbnail_opens_via_xml_entry`
   - `test_video_pick_camera_thumbnail_opens_via_left_thumbnail`
   - `test_video_pick_camera_xml_tap_aborts_if_ui_leaves_camera`
   - `test_video_pick_camera_thumbnail_alternates_retry_targets`
   - `test_video_pick_uses_bounded_create_button_fallback`
