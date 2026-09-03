# Case 78 (03/09/2026): Auto-Dismiss Popup Đồng Bộ Danh Bạ TikTok ("Thêm bạn bè, dùng TikTok thêm vui") & State Machine Integration

## 1. Hiện tượng thực tế (Sự cố Máy 74)
- **Script:** `tiktok-video` (tài khoản `Samnga2403`, folder 587).
- **Mã lỗi:** `upload_subprocess_nonzero` (exit code 1).
- **Hiện trường:** Video 1 đã được đăng và xuất bản thành công lên kênh (có view trên Profile), nhưng TikTok bung popup in-app:
  *"Thêm bạn bè, dùng TikTok thêm vui. Khi đồng bộ danh bạ điện thoại, bạn có thể tìm thấy những người bạn có thể biết và được họ tìm thấy"*
  với 2 nút `OK` và `Không cho phép`.
- **Hậu quả:** State machine kẹt ở state `CAPTION_FILL` do không tìm thấy ô nhập `android.widget.EditText` (bị popup che khuất), sau 3 lần thử thì ném ngoại lệ fail-closed làm tiến độ Excel `Tik3.xlsx` không kịp cập nhật `Video Đã Đăng = 1`.

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Thiếu biến thể chuỗi và nhầm lẫn cơ chế chọn nút Deny:**
   - Trong `automation_core.tiktok.benign_popup`, detector `detect_contact_sync_dialog` thiếu các biến thể text tiếng Việt ("đồng bộ danh bạ điện thoại", "khi đồng bộ danh bạ", "thêm bạn bè, dùng tiktok thêm vui"), tiếng Anh ("sync your phone contacts", "add friends, use tiktok for more fun") và UTF-8 mojibake.
   - Sử dụng `_find_clickable_text` thay vì ưu tiên `_find_exact_label_element` cho nút `Không cho phép`, dễ gây lệch focus hoặc bấm nhầm vào text nền.
2. **Thiếu rule trong `TIKTOK_POPUP_RULES`:**
   - Registry popup `automation_core.tiktok_popup` chưa có rule regex/text nhận diện chuỗi "đồng bộ danh bạ" / "thêm bạn bè, dùng tiktok thêm vui".
3. **State Machine không tự giải phóng popup trước khi tìm ô Caption:**
   - Trong `tiktok-video/scripts/tiktok_workflow/state_machine.py`, các bước `_handle_caption_fill` và `_handle_video_pick` mặc định tìm ngay ô `_find_caption_field`. Nếu có popup che màn hình, script lập tức fail phiên thay vì gọi bộ giải phóng popup lành tính (`_dismiss_core_benign_popup`).
4. **Mock Adapter trong Unit Tests thiếu `_find_ui_element`:**
   - Một số fake Adapter trong unit test chỉ mock `_wait_for_element` mà không có `_find_ui_element`. Việc gọi trực tiếp `adapter._find_ui_element` gây `AttributeError`.

## 3. Giải pháp chuẩn (Case Fix)
1. **Nâng cấp `detect_contact_sync_dialog` trong `automation_core`:**
   - Thêm `body_terms`, `ok_terms`, `deny_terms` hỗ trợ đầy đủ tiếng Việt, tiếng Anh và UTF-8 mojibake.
   - Ưu tiên tìm `_find_exact_label_element` trỏ chính xác vào nút `Không cho phép` / `Don't allow` / `Từ chối`.
   - Giữ nguyên guard `has_sensitive_marker(root)` và `android.widget.EditText` để fail-closed khi có form nhạy cảm.
2. **Thêm Rule `contacts_sync_vi` / `contacts_sync_en` vào `TIKTOK_POPUP_RULES`:**
   - Tự động tap `Không cho phép` / `Don't allow`.
3. **Auto-Dismiss Loop trong State Machine (`tiktok-video`):**
   - Trong `_handle_caption_fill`: Vòng lặp tối đa 5 lần thử tìm `_find_caption_field`. Nếu chưa thấy ô caption, tuần tự gọi các hàm dismiss popup lành tính (`_dismiss_core_benign_popup`, `_deny_tiktok_contacts_settings_prompt`, `_deny_tiktok_contacts_permission`, `_dismiss_location_prompt`, `dismiss_shared_tiktok_popup`), sau đó re-dump UI rồi mới thử lại.
   - Trong `_handle_video_pick`: Gọi `_dismiss_core_benign_popup` ngay trong vòng lặp chờ caption composer xuất hiện sau khi tap Next từ editor.
4. **Helper Safe Adapter Element Finding:**
   - Cung cấp `_find_adapter_element(adapter, xml_text, **kwargs)` kiểm tra `hasattr(adapter, "_find_ui_element")` với fallback về `adapter._wait_for_element(**kwargs)`.
