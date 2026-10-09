# Recovery: VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED & Visual Camera Template Loop

## Triệu chứng
- Alert: `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- Log:
  ```text
  [VIDEO_PICK] Camera surface active without XML upload node; using visual camera upload entry
  [CAMERA] Template surface opened instead of media picker; dismissing template surface
  [CAPCUT_TEMPLATE] Phát hiện màn hình template/hub; tiến hành dismiss
  [CAPCUT_TEMPLATE] Tapping top back/close button at (84, 204)
  [CAMERA] Sau khi dismiss template màn hình không còn là camera surface
  ```

## Nguyên nhân Cốt lõi (Root Cause)
1. **Bố cục Camera TikTok trên máy Samsung:**
   - Bên trái nút chụp (L / BL): Thumbnail album / Thư viện (nút Tải lên để mở Gallery Picker).
   - Bên phải nút chụp (R): Lối tắt mở Template CapCut ("Mẫu") hoặc hiệu ứng.
2. **Visual Target Ordering:**
   - Nếu `_tap_visual_camera_upload_entry` xếp target `R` lên trước (hoặc tính non-dark contrast cho cả 2 nhưng ưu tiên R), script sẽ tap nhầm vào Template CapCut.
3. **Template Dismissal Văng Feed:**
   - Khi mở màn hình Template, `_dismiss_capcut_template_surface` bấm nút close/back ở góc trên bên trái `(84, 150)` hoặc `(84, 204)`.
   - Thao tác back này khiến TikTok đóng luôn Camera và văng về thẳng màn hình Home Feed (`Trang chủ`).
   - Vòng lặp visual retry thấy không còn ở Camera surface nên hủy, hoặc recovery ngoài bấm lại `+` rồi lại tap tiếp vào `R`, dẫn đến cạn timeout và chốt lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## Quy tắc Sửa Code & Invariants (Scope Lock)
1. **Ưu tiên Left Target (L/BL) Tuyệt đối:**
   - Trong `_tap_visual_camera_upload_entry` (`scripts/tiktok_workflow/state_machine.py`), tập hợp các target bên trái (`L`, `BL`) và sắp xếp giảm dần theo non-dark score.
   - Đặt cụm target trái lên đầu danh sách `valid_targets`, target bên phải `R` chỉ là fallback cuối cùng khi bên trái hoàn toàn tối đen (`non_dark < 0.20`).
2. **Auto Re-entry Khi Bị Văng Về Feed:**
   - Sau khi gọi `_dismiss_capcut_template_surface`, nếu màn hình không còn là camera surface (`not self._is_camera_surface_xml(current_xml)`), kiểm tra xem có nút create `+` trên Home feed không (`_find_bounded_create_button`).
   - Nếu có, tap lại nút `+` để vào lại Camera surface tiếp tục retry thay vì return False ngay.
3. **Đồng bộ Unit Tests:**
   - Trong `tests/test_tiktok_workflow.py`, cập nhật các test case mock:
     - `test_tap_visual_camera_upload_entry_stops_if_camera_lost_after_dismiss_template`: Đảm bảo assert Right target không bị tap khi Left target đã được ưu tiên.
     - `test_video_pick_camera_thumbnail_alternates_retry_targets`: Cập nhật sequence bắt đầu từ Left target.
