# AI Auto-Recovery & Popup / Notification Safety Patterns (Session 2026-08-21)

## 1. Tránh chạm nhầm nút Camera [+] ở đáy màn hình
- **Nguyên nhân sự cố:** Các thao tác vuốt từ đáy màn hình (`input swipe 540 1800 ...`) hoặc tap fallback mù (`tap(540, 1700)`) sẽ chạm trúng ngay nút tạo video `[+]` của TikTok.
- **Giải pháp chuẩn:**
  - **Đóng notification shade:** Sử dụng lệnh non-touch duy nhất: `cmd statusbar collapse`. Polling kiểm tra focus, nếu lạc sang app lạ hoặc exception thì fail-closed ngay, tuyệt đối không dùng touch gesture fallback.
  - **Dời vùng fallback:** Mọi thao tác vuốt hoặc tap fallback đều phải nâng lên vùng an toàn `Y = 1200 - 1540` (tránh xa thanh điều hướng `Y = 1800+`).

## 2. Đối soát Profile an toàn (Fail-Closed)
- **Nguyên nhân false mismatch:** Khi kết thúc phiên nuôi, script tap vào "Hồ sơ" nhưng bị lạc vào Camera hoặc overlay khác. Do không thấy `@username`, script cũ vội vàng báo `profile account mismatch`.
- **Quy tắc bắt buộc:**
  - Trong `_verify_profile_after_session`, nếu phát hiện Camera/Overlay, tự động gửi `KEYCODE_BACK` đóng overlay và điều hướng lại Profile qua `tap_navigation_target`.
  - Nếu recovery thất bại hoặc không load được Profile: trả về `profile_verify_status = "camera-recovery-failed"` và fail-closed, tuyệt đối không dùng XML camera để kết luận sai lệch tài khoản.

## 3. Bắt buộc AI sinh code tìm Element XML
- **Quy tắc viết code Auto-Recovery:**
  - AI Vision (Gemini 3.7) bắt buộc phải viết code tìm nút đóng qua `parse_xml`, `iter_elements`, `parse_bounds` và tìm đúng text/content-desc (`"Đóng"`, `"Hủy"`, `"X"`, `"Close"`...) để tính tâm `bounds` động.
  - CẤM hardcode tọa độ mù `ctx.tap(x, y)` nếu element có xuất hiện trong cây XML.
