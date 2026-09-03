# Samsung Keyboard Dumpsys False-Positive & Launcher Recovery Triage

## Bối cảnh & Hiện tượng (Case 54 & Case 53)
Khi chạy `feed_session_smoke` hoặc `multi_machine_feed_session`, máy báo dừng phiên với lỗi:
- `keyboard cleanup command failed on known TikTok screen; swipe recovery (2 swipes) still stuck`
- `unknown TikTok state; swipe recovery (2 swipes) still stuck`

## Nguyên nhân gốc (Root Cause & Anti-Pattern)
1. **Samsung Keypad dumpsys false-positive:**
   - Trên các thiết bị Samsung (`com.sec.android.inputmethod`), output của lệnh `dumpsys input_method` có thể vẫn giữ cờ nội bộ `mIsInputViewShown=true` ngay cả khi bàn phím ảo đã đóng hoàn toàn (`mWindowVisible=false`, `mInputShown=false`, `mShowRequested=false`).
   - Nếu parser `parse_input_method_state` khi `mImeWindowVis` rỗng chỉ nhìn vào `mIsInputViewShown=true`, hệ thống sẽ kết luận nhầm là bàn phím đang mở (False-Positive).
   - Khi đó, flow gửi phím `BACK` để dọn bàn phím ảo không tồn tại, khiến TikTok bị đóng và văng ra Launcher (`com.sec.android.app.launcher`).
2. **False-Positive Startup-Ad / Search-Landing on Launcher (Case 53):**
   - Screenshot trên Launcher bị nhận diện nhầm thành `manual-needed:startup-ad` và `_merge_xml_classification` ghi đè kết quả khi không chặn package Launcher.
   - Widget "Tìm trên điện thoại" trên Launcher bị `detect_search_landing_page` nhận diện nhầm thành TikTok Search Landing.
3. **Kẹt trong Swipe Recovery khi ở Launcher:**
   - Khi bị văng ra Launcher, nếu `_swipe_recovery_on_stuck` gửi lệnh vuốt màn hình `input swipe` trên Launcher thì không có tác dụng và hết 2 lượt vuốt vẫn kẹt, dẫn đến dừng phiên.
4. **Status Bar System Notification gây chặn oan:**
   - Các thông báo hệ thống trên thanh trạng thái (như Google Play "Yêu cầu đăng nhập") có thể lọt vào OCR/XML, nếu không lọc bỏ theo package (`com.android.systemui`) / regex sẽ làm trigger cờ màn hình nhạy cảm (`_is_sensitive`), vô hiệu hóa swipe recovery.

## Giải pháp Chuẩn & Quy trình Triage (Standard Fix)
1. **Gia cố `parse_input_method_state` trong `core/keyboard.py`:**
   - Luôn kiểm tra `mWindowVisible=false` để xác định cửa sổ bàn phím thực sự đã ẩn.
   - Nếu `mIsInputViewShown=true` nhưng cả `mInputShown=false` và `mShowRequested=false`, kết luận bàn phím đã đóng (`visible=False`).
2. **Loại trừ Launcher khỏi Popup Detectors & Merge Classifiers:**
   - Bắt buộc kiểm tra `detect_search_landing_page` loại trừ các launcher package (`com.sec.android.app.launcher`, `app_search_edit_text`, `Tìm trên điện thoại`).
   - Chặn ghi đè `startup-ad` khi `focused_package`/`focus_package` là Launcher hoặc `SystemUI`.
3. **Bọc Relaunch TikTok khi Focus Lost trong Swipe Recovery (Fail-Closed):**
   - Trong `_swipe_recovery_on_stuck`, trước khi vuốt hoặc sau khi vuốt, nếu `_is_launcher_focus_loss` phát hiện thiết bị đang ở Launcher (`com.sec.android.app.launcher`, `systemui`), lập tức gọi `_relaunch_and_poll_tiktok_focus` để mở lại TikTok về Feed trước khi tiếp tục.
   - Nếu focus là external app (không phải Launcher, không phải TikTok) -> fail-closed ngay lập tức, không vuốt mù.
   - Mặc định kiểm tra kết quả `swipe = ctx.adb.shell(...)` phải là `getattr(swipe, "ok", False)`.
4. **Lọc sạch Notification Status Bar trong `_is_sensitive`:**
   - Bỏ qua các node thuộc `com.android.systemui`, `com.sec.android.app.launcher`, `com.google.android.gms` và các node có bounds nằm ở thanh status bar (`bounds y <= 100`) trước khi so khớp từ khóa nhạy cảm; lọc bỏ chuỗi notification Google Play khỏi OCR mà không làm mất các từ khóa bảo mật TikTok.
