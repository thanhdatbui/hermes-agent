# XiaoWei Keyboard (xwkeyboard) Dumpsys False-Positive & Session Duration Tuning

## Vấn đề phát hiện (23/08/2026)
Trên các máy farm Android / S7 chạy daemon bàn phím XiaoWei (`com.android.xwkeyboard/.XwIME`), lệnh `dumpsys input_method` luôn trả về `mInputShown=true` hoặc `mShowRequested=true` mặc dù không có bàn phím hiển thị trên màn hình.

### Hậu quả dây chuyền:
1. Sau mỗi cú swipe (`feed_swipe_smoke`), hàm `_maybe_cleanup_keyboard_on_known_tiktok_screen` kiểm tra trạng thái bàn phím qua `detect_keyboard_state()`.
2. Do dumpsys báo `visible=True`, flow lầm tưởng bàn phím đang mở nên kích hoạt:
   - Gửi phím `BACK` để hạ bàn phím.
   - Thực hiện lại toàn bộ chu trình chụp ảnh (`capture_screenshot`) và đọc XML (`dump_ui_xml`).
3. Chu trình này lặp lại ở **100% các video (13/13 video)**, làm số lần chụp ảnh/dump XML tăng gấp 2–3 lần.
4. Với thời gian chụp/dump trên máy S7 dao động từ 15–30s/lần, toàn bộ thời gian chết do ADB capture chiếm hơn **18.4 phút (72% tổng thời lượng phiên)**, khiến phiên chạy vượt ngưỡng timeout 1500s (25 phút) dù thời gian xem video thật (`watch_delay`) chỉ mất 3.7 phút.

## Cách xử lý chuẩn
1. **Lớp lõi (`automation-core/src/automation_core/keyboard.py`):**
   Trong `parse_input_method_state()`, bỏ qua trạng thái hiển thị ảo của `xwkeyboard`:
   ```python
   if keyboard_package and "xwkeyboard" in keyboard_package.lower():
       return KeyboardState(
           False,
           keyboard_package=keyboard_package,
           ime_name=ime_name,
           source="dumpsys_input_method",
           reason="xwkeyboard input method ignored (virtual daemon without active UI)",
       )
   ```
2. **Cân chỉnh tham số nuôi nick & Timeout (`multi_machine_feed_session.py`):**
   - Giảm số video lướt mỗi phiên: `FEED_SESSION_MIN_TOTAL_VIDEOS = 8`, `FEED_SESSION_MAX_TOTAL_VIDEOS = 11`, `FEED_SESSION_MAX_SWIPES = 12`.
   - Nâng trần timeout thiết bị an toàn: `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1800.0` (30 phút).
