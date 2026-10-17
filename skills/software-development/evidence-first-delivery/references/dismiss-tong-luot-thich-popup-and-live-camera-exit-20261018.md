# Dismiss 'Tổng Lượt Thích' Popup & LIVE Camera Exit Recovery (2026-10-18)

## 1. Hiện Tượng Sự Cố
- **Kẹt Switcher do Popup "Tổng lượt thích":**
  Khi mở Account Switcher trên các phiên bản TikTok mới, sau khi tap Profile, app có thể bung một popup thông báo thành tích milestone *"Tổng lượt thích"* hoặc *"Tổng số lượt thích"*.
  - Nếu không đóng popup này, Account Switcher không thể mở được (`ACCOUNT_SWITCHER_PREPARE_FAILED`).
  - **Cạm bẫy:** Việc dùng tọa độ cứng `tap(540, 1400)` để đóng popup là giải pháp tạm thời, bị Sol Auditor trừ điểm nghiêm trọng (chấm rớt 74/100) vì không thích ứng với các độ phân giải màn hình khác nhau hoặc có thể tap trúng element khác.
- **Kẹt màn hình Camera LIVE sau khi Post:**
  Sau khi xuất bản video, một số luồng giao diện TikTok rơi thẳng vào giao diện Camera phát trực tiếp (LIVE stream creation) thay vì màn hình Feed/Hồ sơ.
  - **Cạm bẫy:** Hardcode `tap(60, 140)` để bấm dấu `[X]` góc trên bên trái không đảm bảo trên các thiết bị có tai thỏ / notch / status bar lệch.

## 2. Giải Pháp Chuẩn Hóa Kiến Trúc
1. **Xử lý Popup "Tổng lượt thích":**
   - Ưu tiên tìm các text/content-desc ngữ nghĩa: `"OK"`, `"Đóng"`, `"Close"`, `"Xong"`.
   - Nếu không có nút bấm rõ ràng, gửi lệnh `adapter.back()` có kiểm soát kết quả.
   - **Bắt buộc Post-condition Assertion & Telemetry:** Dump lại cây UI mới để kiểm tra xem cụm từ *"tổng lượt thích"* còn tồn tại không. Ghi nhận log structured telemetry:
     ```python
     adapter.back()
     time.sleep(0.8)
     fresh_xml = adapter.dump_ui()
     still_present = any(m in fresh_xml.casefold() for m in ("tổng lượt thích", "tổng số lượt thích"))
     logger.info("[POPUP] [TELEMETRY] popup=tong_luot_thich action=back verified_dismissed=%s", not still_present)
     ```
2. **Xử lý thoát Camera LIVE (`_handle_live_camera_exit`):**
   - Quét tìm nút Close theo các resource-id chuẩn của TikTok: `("close", "btn_close", "iv_close", "back_btn", "close_btn")`.
   - Nếu không thấy, gửi `adapter.back()`.
   - Kiểm tra `_is_live_surface(current_xml)` ở vòng lặp sau để đảm bảo đã thoát khỏi màn hình LIVE thật sự.
3. **Unit Tests bắt buộc:**
   - Test `prepare_switcher_anchor` khi có nhiều ứng viên (chọn ứng viên có tọa độ Y cao nhất).
   - Test thoát popup "Tổng lượt thích" qua `back()`.
   - Test thoát LIVE surface qua close button ID và `back()`.
