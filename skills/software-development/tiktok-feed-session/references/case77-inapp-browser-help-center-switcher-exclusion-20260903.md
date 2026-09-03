# Case 77 (2026-09-03): Webview / Help Center "Tài khoản được đề xuất" và Word-Boundary Switcher Exclusion

## Hiện tượng lỗi
- Máy 2 dừng phiên `multi-machine-feed-session` với tài khoản `vjorariw1hg` do báo lỗi `profile verification mismatch: profile account mismatch`.
- Hiện trường thực tế: Trên màn hình hiển thị bài viết Webview Trợ giúp TikTok (`Tài khoản được đề xuất` / Help Center) thay vì mở Account Switcher bottom-sheet.

## Nguyên nhân cốt lõi
1. Khi switch profile hoặc verify profile root, hàm `_find_sticky_profile_header` / fallback anchor nhận nhầm các node/banner chứa chữ "Tài khoản được đề xuất" / "Trợ giúp" làm switcher anchor và tap trúng, mở ra Webview trợ giúp nội bộ TikTok.
2. Màn hình Webview này không được `_detect_inapp_browser` trong `benign_popup_registry.py` nhận diện (do trước đó chỉ nhận diện các từ khóa hẹp như "trình duyệt web", "web browser"), dẫn đến handler không bấm nút đóng hoặc gửi phím Back để thoát.
3. Khi thêm danh sách từ khóa loại trừ `_EXCLUDED_SWITCHER_TERMS`, nếu dùng substring matching `term in text` sẽ gây false-positive loại trừ nhầm các username hợp lệ có chứa chuỗi con như `helpme123` hay `suggested4you`.

## Giải pháp chuẩn
1. **Mở rộng nhận diện Webview / Help Center:**
   - Trong `benign_popup_registry.py`, cập nhật `_detect_inapp_browser` nhận diện các marker: `"trình duyệt web"`, `"web browser"`, `"webview"`, `"tài khoản được đề xuất"`, `"đề xuất tài khoản"`, `"trung tâm trợ giúp"`, `"help center"`, `"support.tiktok.com"`, `"android.webkit.webview"`, `"cross_platform_web_view"`.
   - Cập nhật `_dismiss_inapp_browser` ưu tiên tap nút đóng (`:id/back_btn`, `:id/close`, `:id/btn_back`, etc.) kết hợp fallback `send_device_back_key(ctx)` để tự động thoát Webview về TikTok.
2. **Word-Boundary Switcher Exclusion:**
   - Sử dụng regex word boundary `r"(?i)\b" + re.escape(term) + r"\b"` cho `_EXCLUDED_SWITCHER_TERMS` (`"đề xuất"`, `"suggested"`, `"trợ giúp"`, `"help"`, `"hỗ trợ"`, `"quyền riêng tư"`, `"chính sách"`).
   - Đảm bảo các username hợp lệ như `helpme123` không bị loại trừ sai khỏi switch anchor.
