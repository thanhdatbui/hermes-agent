# Profile & Switcher Popup Recovery Patterns

## 1. Floating Draft Modal / Card (`draft_post_continuation_popup`)
- **Triệu chứng:** Alert `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap` trên Profile screen khi chuyển tài khoản.
- **Hiện trường:** Card nổi *"Tiếp tục chỉnh sửa bài đăng này?"* / *"Continue editing this post?"* che phần header/switch anchor.
- **Nút bấm:**
  - *"Lưu bản nháp"* / *"Save draft"* (bên trái - xám): Đóng popup sạch sẽ và lưu draft.
  - *"Chỉnh sửa"* / *"Edit"* (bên phải - đỏ/cam): Mở editor/camera (CẤM click nút này trong feed session).
- **Quy tắc fix chuẩn:**
  1. Trong `benign_popup_registry.py`:
     - Định nghĩa `_detect_draft_post_continuation`: nhận diện keyword tiếng Việt & tiếng Anh ("tiếp tục chỉnh sửa bài đăng này", "lưu bản nháp", "continue editing this post", "save draft").
     - Định nghĩa `_dismiss_draft_post_continuation`: tìm và tap nút *"Lưu bản nháp"* / *"Save draft"*, fallback `send_device_back_key(ctx)` nếu không tìm thấy.
     - Đăng ký `draft_post_continuation_popup` với priority cao (88).
  2. Trong `feed_swipe_smoke.py`:
     - Thêm `draft_post_continuation_popup` vào `allowlisted_drift_handlers`.
     - Tại switcher guard `_capture_profile_switcher_xml_with_add_phone_guard`: sau khi dismiss popup thành công và màn hình trở về `_is_profile_root_screen`, re-resolve và re-tap `switch_anchor` ngay lập tức để mở switcher sheet.
  3. Trong `tests/test_benign_popup_registry.py`:
     - Viết unit test cho cả tiếng Việt và tiếng Anh, test click nút lưu bản nháp, fallback phím Back, và dispatch qua `dismiss_any_popup`.
