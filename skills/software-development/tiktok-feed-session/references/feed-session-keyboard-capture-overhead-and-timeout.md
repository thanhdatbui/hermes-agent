# Feed Session Keyboard Cleanup Overhead & ADB Screencap Latency Triage

## Bối cảnh
Khi `multi-machine-feed-session` gặp lỗi `run plan max_duration_seconds exceeded before navigate profile` mặc dù preflight đã được tách riêng khỏi ngân sách timeout (1500s):

## 1. Dấu hiệu nhận diện trong `log.jsonl`
1. **Preflight không còn là nguyên nhân:** Thời gian preflight kết thúc nhanh (< 30s), nhưng vòng lặp lướt feed + hậu kỳ tự thân vượt quá 25 phút.
2. **Tỷ lệ thời gian bất thường:**
   - `capture_screenshot` + `dump_ui_xml` chiếm > 70% tổng thời gian phiên (ví dụ 18-20 phút / 25 phút).
   - Thời gian xem video thực tế (`watch_delay`): chỉ chiếm 10-15% (khoảng 3-4 phút).
   - Mỗi video mất từ 70s đến 150s (chủ yếu là thời gian chờ `adb exec-out screencap -p` và ATX dump XML).

## 2. Nguyên nhân cốt lõi: XiaoWei Keyboard Phantom False Positive
1. **XiaoWei IME (`com.android.xwkeyboard`):** Trên một số máy farm (Samsung S7 OneUI), bàn phím ảo XiaoWei liên tục trả về `mInputShown=true` qua `dumpsys input_method` ngay cả khi không có ô input nào được focus và bàn phím không hiện trên màn hình.
2. **Hệ quả lặp lại:**
   - Sau mỗi cú swipe (`swipe_X_after`), `_keyboard_cleanup_candidate` thấy `mInputShown=true` -> kích hoạt `keyboard_cleanup`.
   - `keyboard_cleanup` gửi lệnh `BACK` (`back_keyevent_known_tiktok_screen`).
   - Sau lệnh `BACK`, hệ thống buộc phải chụp lại màn hình (`swipe_X_after_after_keyboard_cleanup`) và dump XML mới.
   - Tiếp tục `gem_blind_probe` lại chụp ảnh/XML thêm một lần nữa.
   - Kết quả: **Mỗi video bị nhân lên 3-4 lần capture screenshot + dump XML**, khiến máy cấu hình thấp bị nghẽn I/O USB/ADB và cạn kiệt deadline 1500s khi số video random từ 12-14 video.

## 3. Quy trình chẩn đoán & Khắc phục
1. **Đo lường phân rã thời gian:**
   - Chạy script phân tích log tính tổng thời gian của từng action (`capture_screenshot`, `dump_ui_xml`, `gem_blind_probe`, `feed_swipe`).
   - Đếm số lần `keyboard_dismiss` / `keyboard_cleanup`. Nếu số lần `keyboard_dismiss` tương đương số video đã lướt, xác nhận dính lỗi phantom keyboard.
2. **Giải pháp xử lý:**
   - **Tạm thời / Vận hành:** Điều chỉnh dải random video xuống **8–11 video** và/hoặc nâng `DEFAULT_DEVICE_TIMEOUT_SECONDS` lên **1800s (30 phút)**.
   - **Gốc rễ:** Bổ sung điều kiện kiểm tra focus hoặc xác thực UI XML thực tế (node bounds bàn phím trên XML) thay vì chỉ tin cậy vào cờ `mInputShown=true` của `dumpsys input_method` đối với package `com.android.xwkeyboard`.
