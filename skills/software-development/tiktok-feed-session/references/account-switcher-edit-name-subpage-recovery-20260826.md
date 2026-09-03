# Chẩn đoán lỗi Account Switcher không mở do kẹt màn hình "Thêm tên" (Edit Name Subpage) & Xử lý điền tên an toàn

## 1. Hiện tượng & Triệu chứng
- **Alert Telegram / Error log:** `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`
- **Màn hình thực tế:** Máy đang mở màn hình con chỉnh sửa tên TikTok:
  - Header: Nút `Hủy` (bounds `[24,72][161,204]`), nút `Lưu` (bounds `[925,72][1056,204]`, ban đầu `enabled=false`)
  - Tiêu đề: `com.ss.android.ugc.trill:id/tv_content_name` (Text: "Tên")
  - Trường nhập: `com.ss.android.ugc.trill:id/hnq` (EditText: "Thêm tên bạn mong muốn")
  - Ghi chú: `Bạn chỉ có thể đổi tên một lần mỗi 7 ngày.`

## 2. Nguyên nhân gốc (Root Cause)
- Khi thực hiện preflight switch account sang tài khoản mục tiêu (`_resolve_profile_switch_anchor` / `_capture_profile_switcher_xml_with_add_phone_guard`), tài khoản hiện tại trên máy đang ở trạng thái chưa đặt tên (profile hiển thị nút/action `"Thêm tên"` thay vì display name).
- Khi script tap vào anchor/vùng header chưa scroll, TikTok hiểu là click vào action "Thêm tên" và điều hướng vào trang chỉnh sửa tên con (`SplashActivity` / `MainActivity` edit name page).
- Khi ở trang con này:
  - Header switcher biến mất.
  - Script capture XML không tìm thấy bottom sheet `Chuyển đổi tài khoản` (`_is_profile_account_switcher_xml` trả `False`).
  - Gửi phím BACK hoặc retry tap vẫn không mở được switcher do đang kẹt trong màn hình con.
  - Script fail-closed an toàn và trả về `manual-needed:account-switcher-not-open`.

## 3. Quy trình xử lý & Điền tên an toàn (Evidence & Recovery)
1. **Evidence First & STOP GATE:**
   - Chụp screencap màn hình gửi `MEDIA:<path>` trên dòng riêng không markdown.
   - Dump UI XML qua ATX session (`capture_atx_session_ui` port 7912) để xác nhận chính xác các node `Hủy`, `Lưu`, `tv_content_name`, `Thêm tên bạn mong muốn`.
2. **Quy trình điền tên chuẩn nếu đang ở màn hình con Edit Name:**
   - Tạo tên tiếng Việt chuẩn: `make_tiktok_name(email)`.
   - Tap focus vào EditText `(540, 576)`.
   - Set bàn phím AdbKeyboard: `adb shell ime set com.github.uiautomator/.AdbKeyboard`.
   - Broadcast text tiếng Việt Base64 an toàn: `am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64>`.
   - Tap nút `Lưu` `(990, 138)` -> bắt dialog xác nhận 7 ngày tap `Xác nhận` `(bounds [541,1104][960,1247])`.
   - Trả lại bàn phím Samsung: `adb shell ime set com.sec.android.inputmethod/.SamsungKeypad`.
3. **Mở Account Switcher:**
   - Sau khi Profile đã có Display Name, thực hiện vuốt nhẹ profile (từ y=0.65h lên y=0.42h, ~400px) để kích hoạt sticky header chứa resource-id `com.ss.android.ugc.trill:id/pcq` (hoặc switcher arrow).
   - Tap vào sticky header để mở bottom sheet "Chuyển đổi tài khoản" và tiến hành switch account bình thường.
