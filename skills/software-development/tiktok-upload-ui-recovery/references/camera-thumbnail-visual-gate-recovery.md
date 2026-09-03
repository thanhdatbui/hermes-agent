# Camera Thumbnail Visual Gate & Retry Recovery (VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED)

## Triệu chứng & Hiện tượng
- Khi upload video trên các máy farm (như Samsung S7, Máy 38), sau khi ấn nút Tạo (+) TikTok mở thẳng vào giao diện Camera (camera-first build).
- Script nhận diện được màn hình Camera (`_is_camera_surface_xml`) và gọi `_tap_visual_camera_upload_entry` để crop góc dưới bên phải nhằm tìm thumbnail ô "Tải lên" / "Upload".
- Tuy nhiên, do video thumbnail tối màu hoặc bo viền tối, tỷ lệ pixel sáng `non_dark` chỉ đạt ~0.25 - 0.30.
- Ngưỡng cũ yêu cầu `non_dark >= 0.45` sẽ từ chối (`Camera upload thumbnail visual gate rejected screenshot`), dẫn đến lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` và fail closed sang `MANUAL_REVIEW`.

## Nguyên tắc xử lý chuẩn (Case UPLOAD-CAMERA-THUMBNAIL-GATE-01)
1. **Ưu tiên XML Selector trước:**
   - Trước khi chụp ảnh/crop visual, kiểm tra xem UIAutomator có dump được node nút Tải lên/thumbnail không: `upload_hot_area`, `view_bg2`, `cwr`, `upload_work`, `Tải lên`, `Upload`.
   - Nếu có, tap ngay qua `_tap_if_found` và đợi xác thực `_is_verified_media_picker_xml`.

2. **Dual Visual Gate (Hỗ trợ cả layout Thumbnail Trái & Phải):**
   - Đặt ngưỡng `non_dark >= 0.20` trong `_tap_visual_camera_upload_entry`.
   - Quét cả 2 vùng:
     - **Góc phải:** `(0.81 * width, 0.77 * height)` đến `(0.94 * width, 0.87 * height)` -> tap tại `(0.875 * width, 0.83 * height)`.
     - **Góc trái (Samsung/biến thể build):** `(0.05 * width, 0.90 * height)` đến `(0.18 * width, 0.99 * height)` -> tap tại `(0.11 * width, 0.95 * height)`.
   - Vẫn bảo đảm chặn màn hình đen hoàn toàn (`non_dark < 0.10`) nhưng chấp nhận được các thumbnail tối / viền bo tròn.
   - Tính an toàn: Kết quả mở thư viện vẫn được xác thực nghiêm ngặt bằng `_is_verified_media_picker_xml` (`has_gallery_nav` + `has_media_tab`), không nhận bừa.

3. **Cơ chế retry tap xen kẽ có giới hạn khi kẹt Camera:**
   - Khi đã tap vào thumbnail mà XML vẫn nhận diện là `_is_camera_surface_xml`, cho phép retry tap thêm (tối đa 4 lần) trong deadline 60s, xen kẽ giữa tọa độ góc trái và góc phải để vượt qua độ trễ UI và tương thích cả 2 biến thể layout.
   - Nếu UI chuyển sang picker thành công thì thoát ngay (`return True`).

4. **Test hồi quy bắt buộc:**
   - `test_video_pick_camera_thumbnail_accepts_darker_preview_tile` (thumbnail tối góc phải).
   - `test_video_pick_camera_thumbnail_opens_via_xml_entry` (mở qua XML node `view_bg2` / `upload_hot_area`).
