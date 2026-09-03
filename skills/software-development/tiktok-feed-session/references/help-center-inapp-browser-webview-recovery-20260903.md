# TikTok In-App Browser & Help Center Webview Recovery (2026-09-03)

## Triệu chứng & Hiện trường
- Khi feed session điều hướng vào Profile hoặc mở Account Switcher để chuyển nick, thiết bị chuyển hướng sang màn hình Webview Trung tâm trợ giúp TikTok (ví dụ: bài viết *"Tài khoản được đề xuất"*, *"Trung tâm trợ giúp"*, URL `support.tiktok.com`).
- Flow quan sát thấy màn hình không phải Profile hay Feed, `_detect_inapp_browser` không nhận diện được do chỉ match các chuỗi hẹp (`trình duyệt web`, `web browser`, `webview`) $\rightarrow$ dừng phiên với lỗi `profile verification mismatch: profile account mismatch` hoặc `profile username/display name anchor is unavailable`.

## Nguyên nhân gốc (Root Cause)
1. **Lệch nhận diện Webview/Help Center**: Bộ phát hiện `inapp_browser_overlay` trong `benign_popup_registry.py` thiếu các tiêu đề bài viết Help Center tiếng Việt phổ biến của TikTok (như *"Tài khoản được đề xuất"*, *"Đề xuất tài khoản"*, *"Trung tâm trợ giúp"*, *"Help Center"*), cũng như class `android.webkit.WebView` hay URL `support.tiktok.com`.
2. **Anchor Selection False-Positive**: Trong lúc tìm node header để mở Switcher (`_find_sticky_profile_header` hoặc generic anchor fallback), nếu màn hình xuất hiện banner gợi ý/trợ giúp quyền riêng tư, script có thể tap nhầm vào link mở bài viết trợ giúp.

## Quy tắc xử lý chuẩn
1. **Mở rộng `_detect_inapp_browser` trong `benign_popup_registry.py`**:
   - Thêm các markers: `"tài khoản được đề xuất"`, `"đề xuất tài khoản"`, `"trung tâm trợ giúp"`, `"help center"`, `"support.tiktok.com"`, `"android.webkit.webview"`, `"cross_platform_web_view"`.
   - `_dismiss_inapp_browser`: Gửi phím BACK (`send_device_back_key(ctx)`) hoặc tap nút đóng (`:id/back_btn`, `:id/close`) để đưa UI quay lại app TikTok chính.
2. **Lọc trừ Switcher Anchor trong `feed_swipe_smoke.py`**:
   - Loại trừ mọi node chứa text/content-desc: `"đề xuất"`, `"suggested"`, `"trợ giúp"`, `"help"`, `"hỗ trợ"`, `"quyền riêng tư"`, `"chính sách"`.
