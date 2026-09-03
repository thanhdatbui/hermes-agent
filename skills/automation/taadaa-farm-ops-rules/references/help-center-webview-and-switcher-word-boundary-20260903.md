# Case 77: Help Center Webview Trap & Switcher Anchor Word-Boundary Filtering (2026-09-03)

## 1. Hiện tượng & Vấn đề gốc (Sự cố Máy 2)
- **Hiện tượng:** Khi chạy feed session hoặc verify profile switcher, script vô tình bấm trúng node/banner chứa văn bản gợi ý/trợ giúp (ví dụ *"Tài khoản được đề xuất"*, *"Trung tâm trợ giúp"*, *"Đề xuất cho bạn"*) thay vì mở menu Account Switcher.
- **Hệ quả:** Màn hình chuyển sang Webview nội bộ TikTok (Help Center `support.tiktok.com` / `com.ss.android.ugc.trill:id/cross_platform_web_view`). Flow không nhận diện được màn hình này là popup/overlay cần đóng nên bị kẹt và báo lỗi `profile verification mismatch: profile account mismatch`, kích hoạt dừng phiên giữ hiện trường.

## 2. Anti-Patterns & Khắc phục
1. **Nhận diện Webview / Help Center trong Benign Popup Registry:**
   - Mở rộng `_detect_inapp_browser` trong `benign_popup_registry.py` để phát hiện các marker:
     `"trình duyệt web"`, `"web browser"`, `"webview"`, `"tài khoản được đề xuất"`, `"đề xuất tài khoản"`, `"trung tâm trợ giúp"`, `"help center"`, `"support.tiktok.com"`, `"android.webkit.webview"`, `"cross_platform_web_view"`, hoặc node `android.webkit.WebView` / resource-id `:id/cross_platform_web_view`, `:id/web_view` kết hợp từ khóa trợ giúp/bảo mật.
   - Nâng cấp `_dismiss_inapp_browser`: Tìm và tap các nút đóng/quay lại (`:id/back_btn`, `:id/close`, `:id/btn_back`, v.v.) kết hợp fallback `send_device_back_key(ctx)` để tự động thoát Webview về lại TikTok.

2. **Quy tắc Word Boundary `\b` khi loại trừ Switcher Anchor:**
   - **Anti-Pattern:** Dùng substring matching lỏng lẻo (`any(term in text for term in _EXCLUDED_SWITCHER_TERMS)`) sẽ vô tình loại trừ các username/handle hợp lệ chứa từ khóa con (ví dụ username `helpme123`, `shelper` bị loại trừ vì chứa chuỗi `"help"`).
   - **Chuẩn hóa:** Luôn sử dụng regex word-boundary `r'(?i)\b' + re.escape(term) + r'\b'` hoặc so khớp chính xác cụm từ khi kiểm tra các từ khóa loại trừ (`_EXCLUDED_SWITCHER_TERMS` bao gồm `"đề xuất"`, `"suggested"`, `"trợ giúp"`, `"help"`, `"hỗ trợ"`, `"quyền riêng tư"`, `"chính sách"`).

3. **Loại bỏ Circular Import:**
   - Tuyệt đối không import chéo các hàm private giữa các module flow (ví dụ import `_capture_xml_text` từ `feed_swipe_smoke.py` vào `benign_popup_registry.py`).
   - Sử dụng các API chuẩn được expose trên context (`ctx.dump_hierarchy()`, `getattr(ctx, 'xml_text', None)`) hoặc qua `automation_core.persistent_ui.capture_atx_session_ui(ctx.adb)`.
