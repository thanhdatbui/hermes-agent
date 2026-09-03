# Hướng dẫn Xử lý Overlay "Vuốt lên để xem thêm" (Swipe-Up Tutorial) & Focus Loss Gating

## 1. Overlay Hướng Dẫn Cử Chỉ "Vuốt lên để xem thêm" (Swipe-Up Tutorial Overlay)
- **Bối cảnh:** Tài khoản mới hoặc TikTok reset gợi ý cử chỉ hiển thị overlay full màn hình với dòng chữ *"Vuốt lên để xem thêm"* / *"Swipe up for more"*.
- **Cách xử lý chuẩn:**
  - Nhận diện: `_detect_swipe_up_tutorial(xml_content, ocr_text)` quét cả XML hierarchy và text OCR.
  - Phải loại trừ trường hợp đang ở màn hình Profile của user khác có các thẻ gợi ý follow / danh sách bạn bè.
  - Xử lý: Thực hiện cử chỉ vuốt dọc từ dưới lên trên qua `input swipe x y_start x y_end 300`.
  - Tọa độ vuốt động: Luôn resolve kích thước màn hình thiết bị (`_resolve_screen_dimensions(ctx)`), ưu tiên `wm size Override` > `device.window_size()` > `config` > `wm size Physical` thay vì fix cứng `1080x1920`.
  - Hậu kiểm (Post-verification): Bounded polling (tối đa 3 lần) kiểm tra lại hierarchy xem overlay đã biến mất và foreground package vẫn là TikTok.

## 2. Gating Focus Mất về Launcher / System UI (Fail-Closed Focus Guard)
- **Nguyên nhân sự cố:** TikTok bị crash hoặc văng về Samsung Launcher / System UI.
  - Các widget trên Launcher (ví dụ: *"Tìm trên điện thoại"* / `app_search_edit_text`) rất dễ bị regex/matcher nhận diện nhầm thành Search Landing hoặc Startup Ad của TikTok.
- **Quy tắc thiết kế an toàn:**
  - **Package Ancestry Check:** Trước khi kích hoạt bất kỳ dismiss handler hoặc popup classifier nào, bắt buộc kiểm tra package của element / container có thuộc `TIKTOK_PACKAGES` (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`).
  - **Exclude Foregrounds:** Loại trừ tuyệt đối các package hệ thống:
    - `com.sec.android.app.launcher`, `com.google.android.apps.nexuslauncher` (Launcher)
    - `com.android.systemui` (System UI / Thanh thông báo / Volume / Dialogs)
    - `com.google.android.gms`, `com.android.vending` (Google Play Services / Notifications)
    - `com.google.android.permissioncontroller` (Hộp thoại cấp quyền hệ thống)
  - **Pre-Swipe Focus Recovery:** Trước mỗi lượt vuốt feed (`_swipe_recovery_on_stuck` / `feed_swipe`), kiểm tra focus foreground package qua `get_focused_activity`. Nếu phát hiện đang ở Launcher hoặc ngoài TikTok, KHÔNG gửi lệnh swipe mù quáng, mà phải kích hoạt `_relaunch_and_poll_tiktok_focus` để mở lại TikTok và chờ focus phục hồi trước khi vuốt tiếp.
