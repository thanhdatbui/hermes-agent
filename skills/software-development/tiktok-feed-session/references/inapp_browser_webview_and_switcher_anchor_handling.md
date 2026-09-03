# In-App Browser / Webview / Help Center & Switcher Anchor Exclusion Guide

## 1. Nguyên nhân lỗi hiện trường
Khi chạy feed session hoặc thao tác đổi nick / verify profile:
- Script có thể vô tình tap trúng banner / link "Tài khoản được đề xuất", "Trung tâm trợ giúp", "Chính sách quyền riêng tư" dẫn đến mở In-app Browser / Webview (`android.webkit.WebView`, `:id/cross_platform_web_view`).
- Nếu popup detector không nhận diện được màn hình này, script sẽ bị kẹt vì không nhận diện được Feed/Profile và dừng máy.
- Nếu hàm tìm Switcher Anchor (`_find_sticky_profile_header`, `find_switcher_anchor`) không lọc bỏ các text trợ giúp/đề xuất, nó có thể nhận nhầm banner "Tài khoản được đề xuất" hoặc "Trung tâm trợ giúp" làm Display Name / Switcher Header và tap mở lại Webview liên tục.

## 2. Cơ chế nhận diện và Dismiss Webview Overlay (`benign_popup_registry.py`)
- **Tên entry:** `inapp_browser_overlay` (Priority: 75).
- **Detector (`_detect_inapp_browser`):**
  - Quét chuỗi trong UI XML & OCR: `"trình duyệt web"`, `"web browser"`, `"webview"`, `"tài khoản được đề xuất"`, `"đề xuất tài khoản"`, `"trung tâm trợ giúp"`, `"help center"`, `"support.tiktok.com"`, `"android.webkit.webview"`, `"cross_platform_web_view"`.
  - Quét node `android.webkit.WebView` hoặc resource-id kết thúc bằng `:id/cross_platform_web_view`, `:id/web_view` kết hợp với các từ khóa trợ giúp/bảo mật/chính sách.
- **Dismisser (`_dismiss_inapp_browser`):**
  - Ưu tiên tìm và tap nút back / close (`:id/back_btn`, `:id/close`, `:id/btn_back`, `:id/btn_close`, `:id/action_bar_left_action`, `:id/iv_back`, hoặc text/desc "đóng", "close", "quay lại", "back").
  - Fallback gửi phím BACK qua `send_device_back_key(ctx)` để thoát Webview về lại TikTok.

## 3. Quy tắc loại trừ Switcher Anchor (`feed_swipe_smoke.py`)
- **Danh sách cấm (`_EXCLUDED_SWITCHER_TERMS`):**
  `("đề xuất", "suggested", "trợ giúp", "help", "hỗ trợ", "quyền riêng tư", "chính sách")`
- **Các vị trí bắt buộc áp dụng:**
  1. `_is_account_like_switcher_text(value)`: loại trừ nếu text chứa bất kỳ từ cấm nào.
  2. `_find_sticky_profile_header(xml_text, identity)`: kiểm tra `expected_display_name`, `display_name_element` và generic header candidate `node` không được chứa từ cấm.
  3. `_profile_switch_fallback_anchor(identity)`: không nhận `username_element` nếu chứa từ cấm.
  4. `_profile_identity_from_xml(xml_text)`: `is_profile_placeholder()` trả về `True` nếu text chứa từ cấm để bỏ qua khi tìm display name.
