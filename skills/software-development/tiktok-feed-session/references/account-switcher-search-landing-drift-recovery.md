# Account Switcher Search Landing Drift & Fallback Anchor Recovery (Case UI-11)

## Bối cảnh & Nguyên nhân lỗi
Khi bot chuẩn bị switch tài khoản trong `_open_profile_account_switcher` (`feed_swipe_smoke.py`), nếu giao diện bị trôi (drift) sang trang Tìm kiếm / Khám phá (Search Landing Page / Explore grid) hoặc tap trượt switch anchor trên header:
1. Candidate XML trả về là giao diện Khám phá thay vì bottom sheet `account_switcher`.
2. Do không có bước quét và giải phóng benign popup/search landing trước guard switcher, và khi retry (`guard_attempt == 2`) `resolved_anchor` tái diễn tọa độ cũ không tác dụng, bot bị fail-closed với lỗi `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`.

## Quy chuẩn Xử lý (Pattern)
1. **Quét & Dismiss Popup trước Switcher Guard:**
   - Trong `_open_profile_account_switcher`, dùng `find_matching_handler(candidate_xml, "")` từ `flows.benign_popup_registry`.
   - Nếu phát hiện `search_landing_overlay` hoặc popup lành tính khác, thực hiện dismiss ngay bằng handler tương ứng và recapture XML sau 1.0s.
2. **Fallback Anchor khi Retry:**
   - Khi tái định vị anchor sau phím `BACK` / re-navigation, nếu `resolved_anchor` trùng bounds với anchor cũ đã tap thất bại và có sẵn `fallback_anchor` (`_profile_switch_fallback_anchor(identity)`):
     -> Chuyển sang dùng `fallback_anchor` (ưu tiên `@username` node) để kích hoạt switcher.
3. **Mở rộng Matcher cho Search Landing Page:**
   - Trong `detect_search_landing_page` (`core/benign_popup.py`), nếu không có nút gắn nhãn `Quay lại` / `Back` cụ thể, fallback sang bất kỳ view clickable nào ở góc trên bên trái `[0,0][250,350]` hoặc hỗ trợ dismiss bằng `KEYCODE_BACK`.
