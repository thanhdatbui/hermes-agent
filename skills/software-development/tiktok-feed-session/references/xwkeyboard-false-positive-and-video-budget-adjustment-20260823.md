# XiaoWei Keyboard Fake Dumpsys Visibility & Feed Duration Budget Adjustment (2026-08-23)

## 1. Vấn đề nghẽn thời gian (Feed Session Timeout)
Khi chạy `multi-machine-feed-session`, máy (đặc biệt các box S7) thường xuyên bị chạm trần timeout `run plan max_duration_seconds exceeded before navigate profile` dù đã tách preflight ra khỏi timeout.

### Phân tích số liệu thực tế từ log máy (Máy 58 - Row 3):
- Tổng thời gian phiên: 1535.4s (25.6 phút) / hạn mức 1500s (25.0 phút).
- Tác vụ xem video thực tế (`watch_delay`): chỉ mất **3.7 phút (14.5%)**.
- Chụp ảnh màn hình (`capture_screenshot`): mất **13.0 phút (50.9%)** (46 lần chụp).
- Lấy UI XML (`dump_ui_xml`): mất **5.4 phút (21.2%)** (44 lần dump).

## 2. Root Cause: False Positive từ bàn phím XiaoWei (`com.android.xwkeyboard`)
- Các máy box farm sử dụng IME ảo XiaoWei (`com.android.xwkeyboard/.XwIME`).
- Khi gọi `adb shell dumpsys input_method`, hệ điều hành luôn trả về `mInputShown=true` (hoặc `mImeWindowVis=0x3`) cho daemon này dù trên màn hình không có bàn phím ảo nào đang mở.
- Hệ quả: Sau **mỗi cú swipe**, hàm `_maybe_cleanup_keyboard_on_known_tiktok_screen` tưởng có bàn phím nên bấm `BACK` và bắt buộc chụp lại screenshot + dump UI XML lần 2.
- Việc chụp lặp 2-3 lần cho mỗi video nhân thời gian xử lý mỗi video lên tới **90s – 110s/video**, khiến việc lướt 13-14 video tốn hơn 25 phút.

## 3. Giải pháp đã thực hiện

### 3.1. Bỏ qua fake dumpsys visibility cho `xwkeyboard`
Trong `automation_core/src/automation_core/keyboard.py` (`parse_input_method_state`):
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
- Cắt giảm ngay **~50% số lần chụp ảnh và dump XML thừa**.
- Rút ngắn thời gian mỗi video từ ~90–110s xuống còn ~30–45s/video.

### 3.2. Điều chỉnh Video Budget & Timeout
Trong `python_runner/flows/multi_machine_feed_session.py`:
- `FEED_SESSION_MIN_TOTAL_VIDEOS = 8` (trước: 10)
- `FEED_SESSION_MAX_TOTAL_VIDEOS = 11` (trước: 14)
- `FEED_SESSION_MAX_SWIPES = 12` (trước: 15)
- `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1800.0` (30 phút, trước: 1500s / 25 phút).
