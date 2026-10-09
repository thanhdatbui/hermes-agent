# Case 83: Phân Định Camera Surface vs Profile Root & Phục Hồi Kẹt Màn Hình Phát Video Cá Nhân

## 1. Hiện Tượng & Triệu Chứng
- **Lỗi:** `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control` (exit code 1).
- **Hiện trường live:** Máy kẹt tại màn hình xem chi tiết video cá nhân trên kênh (Profile video playback surface) thay vì Camera hoặc Media Picker.
- **Dấu hiệu nhận diện trên UI:**
  - Nút cài đặt riêng tư: `:id/sl0`, text `"Cài đặt quyền riêng tư"` / `"Privacy settings"`.
  - Thống kê lượt xem cá nhân: `:id/view_entrance_text`, text `"lượt xem"`.
  - Nút quay lại góc trên trái: `:id/bq7`, `content-desc="Quay lại"`.

---

## 2. Nguyên Nhân Gốc Rễ (Anti-Pattern)
1. **False-Positive trong `_is_camera_surface_xml`:**
   - Bộ lọc cũ chỉ kiểm tra `any(m in folded for m in (... 'content-desc="camera"', 'text="đăng"', 'text="tạo"'))`.
   - Trên màn hình Profile root:
     - Header có nút mở camera/story với `content-desc="Camera"`.
     - Tab video của kênh có `text="Đăng"`.
   - Kết quả: `_is_camera_surface_xml` nhận nhầm Profile root là Camera!
2. **Tap mù rơi vào video tile:**
   - Khi camera mở ở chế độ LIVE/Template và gọi `_dismiss_capcut_template_surface`, UI thoát khỏi camera về lại Profile.
   - Do `_is_camera_surface_xml` vẫn trả về `True` cho Profile root, hàm `_tap_visual_camera_upload_entry` tiếp tục fallback tap mù vào tọa độ thumbnail alternative `(156, 1574)`.
   - Tọa độ này trên Profile rơi trúng video tile đầu tiên của kênh, mở màn hình phát video chi tiết.
3. **Kẹt luồng phục hồi:**
   - Luồng `_recover_video_pick_create_entry` không nhận diện được màn hình video playback, không tìm thấy nút create (+), dẫn đến fail-closed.

---

## 3. Giải Pháp Kỹ Thuật Chuẩn Hóa

### A. Thắt chặt nhận diện Camera Surface (`_is_camera_surface_xml`)
Bắt buộc loại trừ 4 nhóm bề mặt trước khi quét từ khóa camera:
1. `_is_profile_video_playback_surface(xml)`: Nếu là màn hình phát video cá nhân -> `False`.
2. `_has_gallery_surface_markers(xml)`: Nếu là gallery/media picker -> `False`.
3. Profile root markers: `"sửa hồ sơ"`, `"chỉnh sửa hồ sơ"`, `"edit profile"`, `"chia sẻ hồ sơ"`, `"thêm tiểu sử"`, `"hoàn tất hồ sơ"`, `":id/ny0"`, `"/ny0"`.
4. Bottom Navigation Bar: Có cả `Trang chủ` (`text="trang chủ"` / `content-desc="trang chủ"`) VÀ `Hồ sơ` (`text="hồ sơ"` / `content-desc="hồ sơ"`).
5. Feed root: Có `long_press_layout` kèm `dành cho bạn` / `đang follow`.

### B. Nhận diện & Thoát màn hình xem video cá nhân
- **Predicate:** `_is_profile_video_playback_surface(xml_text)`:
  - Kiểm tra `(has_privacy_btn or has_view_entrance) and (has_back_btn or ":id/sl0" in lowered)`.
- **Recovery:** `_recover_profile_video_playback_surface(adapter, xml_text)`:
  - Tìm node `:id/bq7` / `content-desc="Quay lại"` ở `top <= 400` và tap chính xác vào tâm nút.
  - Fallback nếu không parse được tọa độ: gọi `adapter.back()`.
  - Tích hợp vào `_recover_video_pick_create_entry`, `_wait_for_verified_media_picker_after_recovery`, và các vòng lặp chờ upload picker trong `_handle_video_pick`.

### C. Gate kiểm tra sau Dismiss Template
- Trong `_tap_visual_camera_upload_entry`: Sau khi gọi `_dismiss_capcut_template_surface`, bắt buộc re-dump XML và kiểm tra `_is_camera_surface_xml(current_xml)`.
- Nếu UI đã văng về Profile/Feed (không còn là Camera), ngắt ngay việc tap alternative thumbnail và trả về `False` để outer flow định hướng lại bằng `+` button.
