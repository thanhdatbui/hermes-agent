# Avatar & Account Switcher UI Recovery (TikTok 46.x - Case 79)

## 1. Avatar-Only Batch Execution vs "LIVE ĐĂNG VIDEO" Log Confusion
- Script `run_tiktok_upload_avatar.ps1` chạy chế độ Avatar-Only độc lập bằng cách thiết lập `-ForceAvatarMachineList <list>` hoặc `-WorkerId hermes-kibe-avatar`.
- **Lưu ý giao tiếp User:** Output PowerShell có thể in dòng tiêu đề kế thừa từ launcher cha: `Chế độ: LIVE ĐĂNG VIDEO`. Phải giải thích rõ ngay cho user rằng:
  - Hệ thống chỉ thực hiện các bước: `CONNECT_DEVICE` -> `ACCOUNT_SWITCHER` -> `ACCOUNT_READY` -> `ENSURE_AVATAR` (push ảnh, chọn ảnh trong picker, crop và lưu avatar).
  - Ngay sau khi avatar được cập nhật thành công, workflow tự động force-stop TikTok, dọn dẹp file tạm trên thiết bị và chuyển thẳng về `RELEASE`.
  - Các bước `MEDIA_PUSH`, `VIDEO_PICK`, `CAPTION_FILL`, `POST`, `UPDATE_WORKBOOK` hoàn toàn bị bỏ qua.

## 2. TikTok 46.x Profile Account Switcher Anchor Failure & Static Username Pitfall
- **Hiện tượng:** Máy kẹt `ACCOUNT_VERIFY_MISMATCH` hoặc `SWITCHER_NOT_CONFIRMED` khi cố gắng mở switcher từ Profile root.
- **Nguyên nhân cốt lõi:**
  1. Trên TikTok 46.x, node text `@username` (`com.ss.android.ugc.trill:id/sxa` ở tọa độ Y ~616px) là **text tĩnh** (tap vào chỉ copy username hoặc không có phản hồi).
  2. Node mở Account Switcher thực tế là **Display Name** (`com.ss.android.ugc.trill:id/sv6` ở tọa độ Y ~552px).
  3. Ở đầu trang cá nhân thường có banner Story prompt (`:id/pxu` - "Tám chuyện nào" / "Bạn đang nghĩ gì...") nằm ở `Y=120..292`. Nếu tap trúng vùng này sẽ mở banner tạo Story thay vì mở Account Switcher.
- **Giải pháp chuẩn:**
  1. Trong `sanitize_switcher_profile_xml`: Xóa sạch `text` và `content-desc` của các node `:id/sxa` và `:id/pxu` trên XML in-memory trước khi đưa vào `find_switcher_anchor`.
  2. Nâng `header_limit` lên `max(650, int(screen_height * 0.35))` trong `prepare_switcher_anchor` để bắt được Display Name ở `top=519`.
  3. Blacklist các từ khóa chỉ số mạng xã hội (`"đang follow"`, `"follower"`, `"thích"`, `"like"`, `"following"`, `"bạn bè"`, `"video"`, `"bài đăng"`) khỏi danh sách candidate header để không bị nhầm lẫn với Display Name.

## 3. In-Memory Element Traversal trong Avatar Picker (Tránh Chờ Lồng Gây Treo Máy)
- **Hiện tượng:** Máy kẹt tại bước `AVATAR_SELECTION_FAILED` hoặc mất 5-10 phút tại màn hình chọn ảnh từ gallery picker.
- **Nguyên nhân cốt lõi:** Hàm `_find_adapter_element` gọi lồng `adapter._wait_for_element(**kwargs)` cho từng resource ID trong danh sách fallback (`o_9`, `xip`, `wrj`, `rts`, `qii`, `rou`, `sca`), khiến mỗi lần kiểm tra bị sleep tích lũy 60s x 7 = 420 giây.
- **Giải pháp chuẩn:**
  - `_find_adapter_element` **CHỈ tra cứu trực tiếp in-memory** qua `adapter._find_ui_element(xml_text, **kwargs)` trên XML đã dump sẵn.
  - Vòng lặp chờ nút Tiếp / Crop sử dụng polling ngắn (25s deadline) và fallback tap tọa độ resolution-aware `(924, 1842)`.

## 4. Post-Switch Benign Popup & Login Save Handling tại `ACCOUNT_READY`
- **Hiện tượng:** Sau khi tap chọn tài khoản trong switcher, TikTok hiển thị popup `save_login` ("Lưu thông tin đăng nhập") hoặc story onboarding, che khuất Profile root khiến `verify_selected_account` bị fail.
- **Giải pháp chuẩn:**
  - Trong `_handle_account_ready`, thiết lập vòng lặp polling 20s:
    1. Dump UI XML hiện tại.
    2. Tự động gọi `_dismiss_simple_close_popup` để đóng các banner Story và popup `save_login`.
    3. Thử `verify_selected_account`. Nếu chưa match, gọi `adapter.tap_profile()` để kéo giao diện về Profile root và thử lại.
