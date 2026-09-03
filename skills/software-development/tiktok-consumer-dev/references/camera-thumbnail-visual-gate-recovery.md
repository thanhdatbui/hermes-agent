# Camera Thumbnail Visual Gate & Retry Recovery (VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED)

## Triệu chứng & Hiện tượng
- Khi upload video trên các máy farm (như Samsung S7, Máy 38), sau khi ấn nút Tạo (+) TikTok mở thẳng vào giao diện Camera (camera-first build).
- Script nhận diện được màn hình Camera (`_is_camera_surface_xml`) và gọi `_tap_visual_camera_upload_entry` để crop góc dưới bên phải nhằm tìm thumbnail ô "Tải lên" / "Upload".
- Tuy nhiên, do video thumbnail tối màu hoặc bo viền tối, tỷ lệ pixel sáng `non_dark` chỉ đạt ~0.25 - 0.30.
- Ngưỡng cũ yêu cầu `non_dark >= 0.45` sẽ từ chối (`Camera upload thumbnail visual gate rejected screenshot`), dẫn đến lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` và fail closed sang `MANUAL_REVIEW`.

## Nguyên tắc xử lý chuẩn (Case UPLOAD-CAMERA-THUMBNAIL-GATE-01)
1. **Hạ ngưỡng visual gate:**
   - Đặt ngưỡng `non_dark >= 0.20` trong `_tap_visual_camera_upload_entry`.
   - Vẫn bảo đảm chặn màn hình đen hoàn toàn (`non_dark < 0.10`) nhưng chấp nhận được các thumbnail tối / viền bo tròn.
   - Tính an toàn: Kết quả mở thư viện vẫn được xác thực nghiêm ngặt bằng `_is_verified_media_picker_xml` (`has_gallery_nav` + `has_media_tab`), không nhận bừa.

2. **Cơ chế retry tap có giới hạn khi kẹt Camera:**
   - Khi đã tap vào thumbnail tại `(width * 0.875, height * 0.83)` mà XML vẫn nhận diện là `_is_camera_surface_xml`, cho phép retry tap thêm (tối đa 3 lần) trong deadline 60s để vượt qua độ trễ UI trên thiết bị yếu.
   - Nếu UI chuyển sang picker thành công thì thoát ngay (`return True`).

3. **Test hồi quy bắt buộc:**
   - Test `test_video_pick_camera_thumbnail_accepts_darker_preview_tile` giả lập thumbnail tối (~28% non_dark) bảo đảm pass.
