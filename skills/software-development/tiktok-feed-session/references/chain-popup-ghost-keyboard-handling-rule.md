# Quy tắc xử lý Chain Popup (Popup liên hoàn) và Ghost Keyboard State

## 1. Hiện tượng & Triệu chứng
- Cảnh báo Telegram báo lỗi dừng phiên: `keyboard remained visible after dismiss attempt` (hoặc `status: manual-needed`).
- Tuy nhiên trên screenshot đính kèm thực tế: **Không hề có bàn phím ảo** mà lại đang hiển thị một popup/dialog khác (ví dụ: popup xin quyền Facebook *"Cho phép TikTok có quyền truy cập vào email và danh sách bạn bè trên Facebook của bạn?"*).
- Máy bị khóa giữ hiện trường (`device-locks`) dù các popup xuất hiện đều là benign popup đã có handler.

## 2. Nguyên nhân gốc rễ (Root Cause Chain)
1. **Ghost IME State (`dumpsys input_method`):**
   - Khi đóng một popup có chứa text input (như popup Add Phone), bàn phím ảo đã tắt nhưng dịch vụ bàn phím hệ thống (đặc biệt là SamsungKeypad `com.sec.android.inputmethod` trên Android 7/8/9) vẫn trả về `mInputShown=true` hoặc `mShowRequested=true`.
   - Hàm `detect_keyboard_state` khi thấy UI XML không có node bàn phím thì lại fallback sang `dumpsys input_method`, dẫn đến cờ `keyboard_visible=True` sai (ghost keyboard).

2. **Gãy nhánh Fallback khi gặp Chain Popup (Popup nối tiếp):**
   - `dismiss_keyboard_after_add_phone` cố gắng dọn bàn phím bằng tap hoặc phím BACK.
   - Khi kiểm tra trạng thái màn hình sau đó, hàm `_is_known_tiktok_screen_after_add_phone` chỉ chấp nhận các màn hình feed/profile chuẩn (`home, for-you, following, friends, profile`).
   - Nếu màn hình tiếp theo là một popup nối tiếp (như popup Facebook `manual-needed:popup`), hàm coi đây là màn hình không hợp lệ (`unknown/manual-needed`), hủy bỏ luồng fallback và trả về lỗi `keyboard remained visible after dismiss attempt`.

3. **Bị chặn trước khi tới Handler của Popup thứ 2:**
   - Do bị ngắt ngay tại bước hậu xử lý của popup thứ nhất (Add Phone), runner không kịp chuyển tiếp sang `BENIGN_POPUP_REGISTRY` hay `dismiss_allowed_generic_popup` để xử lý popup thứ hai.
   - Luồng cứu hộ `_swipe_recovery_on_stuck` kích hoạt vuốt 2 lần nhưng không có tác dụng trên modal dialog, dẫn đến dừng phiên.

## 3. Quy chuẩn xử lý (Fix Pattern)
1. **Ưu tiên bằng chứng XML thực tế trước Dumpsys IME:**
   - Khi UI XML đã được dump đầy đủ và không chứa bất kỳ node bàn phím nào thuộc các package bàn phím đã biết hoặc các nút điều khiển bàn phím, không được coi bàn phím đang hiển thị chỉ dựa trên `mInputShown=true` cũ của dumpsys.
2. **Hỗ trợ chuỗi Popup liên hoàn (Chain Popup Transition):**
   - Sau khi đóng một popup, nếu màn hình sau đó là một benign popup khác (`manual-needed:popup` được nhận diện bởi `detect_allowed_generic_popup` hoặc `BENIGN_POPUP_REGISTRY`), không được coi là lỗi bàn phím hay lỗi màn hình lạ.
   - Phải tiếp tục chuyển giao sang handler của popup kế tiếp để xử lý trọn vẹn trước khi kiểm tra màn hình gốc.
3. **Loại trừ modal dialog khỏi `_swipe_recovery`:**
   - Nếu màn hình sau khi đóng popup vẫn là modal dialog có nút chọn (như `Không cho phép`, `Hủy`), `_swipe_recovery` không được vuốt mù mà phải fail-closed hoặc gọi đúng action click của popup đó.
