# CapCut Template Preview Blocking Recovery

## Dấu hiệu & Triệu chứng
- **Triệu chứng:** Farm alert `upload_subprocess_nonzero` hoặc `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
- **Dấu hiệu UI:**
  - Màn hình CapCut template preview xuất hiện sau khi mở camera TikTok hoặc khi tap nút create/upload.
  - Chứa nút CTA `"Thử mẫu này"` / `"Use this template"`, `"Thử mẫu trong CapCut"`.
  - Tên template tác giả `"Bởi Capcut của..."` / `"CapCut"`.
  - Nút quay lại/đóng `<` ở thanh header trên cùng (top <= 400).
- **Hậu quả:** Che khuất luồng TikTok media picker / feed root, khiến flow bị kẹt ở camera/template surface và không mở được gallery picker.

## Cơ chế xử lý (Protocol)
1. **Phân loại bề mặt (`_is_capcut_template_surface`):**
   - Quét các label (`text`, `content-desc`): match `"thử mẫu này"`, `"thử mẫu trong capcut"`, `"use this template"`, `"bởi capcut"`, `"mẫu capcut"`.
   - Loại trừ nếu bề mặt đã là `_is_verified_media_picker_xml`.
2. **Dismiss an toàn (`_dismiss_capcut_template_surface`):**
   - B1: Tìm node nút Back / Close ở dải header trên cùng (`top <= 400`, `desc/text` in `{"quay lại", "back", "đóng", "close", "<"}` hoặc `resource-id` kết thúc bằng `back/close`) và tap chính xác.
   - B2: Nếu không tìm thấy node nút Back, gửi lệnh semantic `adapter.back()` có kiểm soát (budget 2 lần).
   - B3: Recapture UI để xác nhận màn hình template đã thoát.
3. **Phòng vệ ở các entry point:**
   - `_wait_for_feed`: Dismiss template preview nếu xuất hiện khi chờ feed.
   - `_leave_tiktok_subpages`: Dismiss template preview trước khi navigate Profile root.
   - `_handle_dismiss_popups`: Dismiss template preview trong các vòng lặp dọn popup.
   - `_tap_visual_camera_upload_entry`: Nếu tap thumbnail camera mà bị nảy vào CapCut template preview, dismiss template và chuyển ngay sang alternative target (ví dụ: left thumbnail thay vì right thumbnail).
   - `_normalize_to_home_for_video_pick` & `_recover_video_pick_create_entry`: Tự động dismiss template khi khôi phục Home root.
4. **Root surface guard:**
   - Cập nhật `_is_tiktok_root_surface` (state_machine) và `is_profile_root` (adapter) để loại trừ các marker của template CapCut, tránh nhận nhầm template preview là root feed/profile.
