# Tránh tap nhầm link Trợ giúp/Đề xuất mở In-App Webview khi switch account (2026-09-03)

## Hiện tượng & Nguyên nhân
- Khi xác thực danh tính hoặc chuyển đổi profile TikTok (`_find_sticky_profile_header`), nếu giao diện Profile có chứa banner hoặc link Trợ giúp/Đề xuất ("Tài khoản được đề xuất", "Quyền riêng tư", "Chính sách"), bộ lọc switcher header có thể so khớp nhầm node này thành switcher anchor.
- Thao tác tap vào node này kích hoạt màn hình In-App Webview Trợ giúp (`support.tiktok.com` / `android.webkit.WebView`), khiến flow bị văng khỏi TikTok và dừng máy với lý do `profile account mismatch`.

## Giải pháp đã triển khai (tiktok-luot nuoi acc)
1. **Loại trừ từ khóa trợ giúp/đề xuất khỏi Switcher Header (`feed_swipe_smoke.py`)**:
   - Thêm `_EXCLUDED_SWITCHER_TERMS` bao gồm: `"đề xuất"`, `"suggested"`, `"trợ giúp"`, `"help"`, `"hỗ trợ"`, `"quyền riêng tư"`, `"chính sách"`.
   - Áp dụng kiểm tra trong `_find_sticky_profile_header`, `_is_account_like_switcher_text`, `_profile_switch_fallback_anchor`, `_profile_identity_from_xml` để không nhận nhầm link trợ giúp làm header hoặc tài khoản.
2. **Nhận diện & Tự động phục hồi Webview Trợ giúp (`benign_popup_registry.py`)**:
   - Mở rộng `_detect_inapp_browser` để phát hiện các màn hình Webview Trợ giúp có chứa text `"tài khoản được đề xuất"`, `"đề xuất tài khoản"`, `"trung tâm trợ giúp"`, `"help center"`, `"support.tiktok.com"`, hoặc node `android.webkit.WebView` / resource-id `:id/cross_platform_web_view`, `:id/web_view`.
   - Cập nhật `_dismiss_inapp_browser` ưu tiên tìm và bấm nút Đóng / Quay lại (`:id/back_btn`, `:id/close`), đồng thời kết hợp `send_device_back_key(ctx)` để đưa app về lại TikTok.
3. **Quy tắc chạy Canary Batch Feed**:
   - Chạy `run_tiktok.py` với mode `multi-machine-feed-session`: bắt buộc truyền `--account-workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx"` cùng `--recovery-test-swipes 2 --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --prepare-tiktok`.
