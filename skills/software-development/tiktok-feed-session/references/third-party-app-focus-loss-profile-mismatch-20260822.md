# Chẩn đoán lỗi False Profile Mismatch do App thứ 3 (Outlook/System UI) cướp Focus (2026-08-22)

## Hiện tượng & Sự cố thực tế (Máy 46 - Ca row-2 ngày 22/08)
- **Script:** `multi-machine-feed-session` / `feed-session-smoke`.
- **Thông báo Farm Alert:** `🚨 [MÁY 46] DỪNG PHIÊN - Lý do: profile account mismatch and profile username/display name anchor is unavailable`.
- **Hiện trạng máy:** Đã về màn hình Home an toàn sau cleanup. Nick trên máy thực tế đúng 100% với workbook (`@trieutruc0505`).

## Phân tích Call Chain & Root Cause
1. **Tiến trình điều hướng Hồ sơ:**
   - Flow gọi `tap_navigation_target(profile)` thành công và TikTok hiển thị đúng profile `@trieutruc0505`.
   - Bước `profile_preflight_identity_guard` dump XML lần 1 xác nhận `detected_screen = "profile"`, có đầy đủ node `@trieutruc0505`.
2. **App thứ 3 tự bật cướp quyền (Focus Loss):**
   - Giữa bước guard và bước resolve identity/switch anchor, ứng dụng **Microsoft Outlook** (`com.microsoft.office.outlook`) bất ngờ mở màn hình chào mừng / đăng nhập (`Chào mừng bạn đến với Outlook`, `THÊM TÀI KHOẢN`, `TẠO TÀI KHOẢN MỚI`).
3. **Hiệu ứng domino dẫn đến False Alarm:**
   - Khi `_capture_xml_text(ctx, "profile_switch_anchor_initial")` hoặc guard thứ 2 chụp UI, XML thuộc về `com.microsoft.office.outlook`.
   - `_profile_identity_from_xml` không tìm thấy node `@username` (hoặc lấy `display_name` rác từ Outlook).
   - Script đánh giá là sai nick (`current != expected`) và cố gắng tìm anchor đổi tài khoản (`_resolve_profile_switch_anchor`).
   - Màn hình Outlook không có switcher anchor của TikTok -> `switch_anchor is None` -> Flow phát sinh lỗi:
     `profile account mismatch and profile username/display name anchor is unavailable`.

## Quy tắc chẩn đoán & Pitfall
- Khi gặp alert `profile account mismatch and profile username/display name anchor is unavailable`, **không vội kết luận máy bị đổi nick hay sai slot**.
- **Kiểm tra ngay `package` của UI XML tại thời điểm fail:**
  - Nếu `package != "com.ss.android.ugc.trill"`, đây là sự cố **Focus Loss do App ngoài đè màn hình**, không phải lỗi logic so khớp tài khoản.
  - Kiểm tra xem app ngoài có thể force-stop / disable notification để tránh tái diễn hay không.
- **Xác minh hiện trường:** Luôn đọc XML ở bước ngay trước khi fail (`profile_preflight_identity_guard`) để đối chiếu xem nick thực tế đã mở đúng hay chưa trước khi app ngoài xuất hiện.
