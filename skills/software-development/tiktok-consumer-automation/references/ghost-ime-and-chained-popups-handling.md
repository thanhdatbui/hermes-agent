# Ghost IME State & Chained Popups Handling After Add Phone Dismiss

## Triệu chứng
- Trên máy Samsung Galaxy S7 (Android 7-8), sau khi đóng popup "Thêm số điện thoại" (Add Phone), flow kiểm tra bàn phím và báo lỗi: `keyboard remained visible after dismiss attempt`.
- Màn hình thực tế hiển thị popup kế tiếp (ví dụ: Popup Facebook "Cho phép TikTok truy cập danh bạ/email" hoặc Popup quyền cài đặt danh bạ), không có bàn phím ảo nào đang mở.

## Nguyên nhân gốc rễ
1. **Ghost IME Visibility từ dumpsys:**
   - Lệnh `dumpsys input_method` giữ cờ `mInputShown=true` / `mShowRequested=true` cũ của bàn phím Samsung (`com.sec.android.inputmethod` / `SamsungKeypad`) ngay cả khi bàn phím đã biến mất khỏi màn hình.
   - Nếu hàm `detect_keyboard_state` có UI XML hợp lệ nhưng lại bỏ qua kết quả XML không có bàn phím và rơi xuống `dumpsys input_method`, nó sẽ báo sai `visible=True`.
2. **Thiếu package bàn phím Samsung trong allowlist:**
   - Danh sách `KNOWN_KEYBOARD_PACKAGES` trước đó chỉ có `com.samsung.android.honeyboard` (Samsung đời mới), thiếu `com.sec.android.inputmethod` (Samsung đời cũ như S7).
3. **Chuỗi Popup liên hoàn (Chained Popups):**
   - Khi đóng Add Phone, TikTok có thể lập tức mở tiếp một popup benign khác (`manual-needed:popup` như Facebook/Contacts permission, `packageinstaller/system-dialog`, `account-update-prompt`).
   - Hàm `_is_known_tiktok_screen_after_add_phone` trước đây chỉ chứa các màn hình chuẩn (`home, for-you, profile, friends, following`). Khi gặp `manual-needed:popup`, fallback cho rằng màn hình bị lạc/lỗi và ngắt luồng với lỗi `keyboard remained visible after dismiss attempt`, ngăn không cho flow chuyển tiếp sang Registry để bấm "Không cho phép".

## Giải pháp chuẩn hóa
1. **Đưa `com.sec.android.inputmethod` vào `KNOWN_KEYBOARD_PACKAGES`:** Đảm bảo mọi dòng máy Samsung trên farm đều được nhận diện đúng.
2. **UI XML là Single Source of Truth:** Trong `detect_keyboard_state`, nếu có `xml_path` đọc được và XML không chứa node bàn phím nào, trả về ngay `KeyboardState(visible=False, source="ui_xml")`, không để `dumpsys input_method` ghi đè.
3. **Mở rộng Allowlist màn hình sau Add Phone:**
   Bổ sung `GENERIC_POPUP_SCREEN` (`manual-needed:popup`), `PACKAGEINSTALLER_DIALOG_SCREEN`, `ACCOUNT_UPDATE_PROMPT_SCREEN`, `VERIFY_EMAIL_PROMPT_SCREEN`... vào `_KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE` và `_blocked_after_close_reason` để flow chuyển tiếp mượt sang Registry giải quyết popup tiếp theo.
