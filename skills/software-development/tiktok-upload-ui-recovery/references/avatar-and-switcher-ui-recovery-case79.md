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

## 5. ENSURE_AVATAR: Tránh Bẫy `bring_to_foreground` Đẩy Lùi Về Feed & Nhận Diện Profile Root Scrolled
- **Hiện tượng:** Chạy Avatar-Only (`run_tiktok_upload_avatar.ps1`) hoàn tất xác minh tài khoản ở `ACCOUNT_READY`, nhưng sang `ENSURE_AVATAR` thì bị lỗi `[AVATAR_WORKFLOW_FAILED] ENSURE_AVATAR: Avatar workflow failed: PROFILE_ROOT_NOT_CONFIRMED: Profile root was not confirmed`.
- **Nguyên nhân cốt lõi:**
  1. Khi qua `ACCOUNT_READY`, bước quét grid video (`scan_profile_grid`) cuộn màn hình xuống dưới làm nút *"Sửa hồ sơ"* trôi khỏi màn hình hiện tại.
  2. Tại `ENSURE_AVATAR`, `_looks_like_profile_root` chỉ kiểm tra hẹp 4 từ khóa: `"sửa hồ sơ"`, `"edit profile"`, `"thêm tiểu sử"`, `"add bio"`. Do nút đã bị cuộn trôi, hàm trả về `False`.
  3. Khi thấy `False`, code cũ gọi mù `adapter.bring_to_foreground(package)`. Lệnh này chạy `am start -n .../.MainActivity`. Do TikTok đang chạy foreground sẵn, intent này kích hoạt lại `SplashActivity` và đẩy app văng ngược về video Feed (Tab Trang chủ `selected="true"`).
  4. Từ Feed, `open_profile_root` cố gắng tap tab Hồ sơ nhưng dễ bị overlay video hoặc misread bottom-nav cản trở, dẫn đến fail toàn bộ flow avatar sau 3 attempts.
- **Giải pháp chuẩn:**
  1. **Chặn `bring_to_foreground` khi đã ở foreground:**
     Chỉ gọi `bring_to_foreground` khi app thực sự chưa ở foreground:
     `if not adapter._package_is_foreground(package) and adapter.bring_to_foreground(package):`
     Tuyệt đối không gửi intent `MainActivity` khi app đã ở foreground vì sẽ làm reset ngữ cảnh Profile về Home Feed.
  2. **Mở rộng nhận diện `_looks_like_profile_root`:**
     - Bổ sung các marker Profile: `"chia sẻ hồ sơ"`, `"menu hồ sơ"`.
     - Kiểm tra trạng thái tab Bottom Navigation: nếu node có `'selected="true"'` đi kèm `'content-desc="hồ sơ"'` hoặc `'text="hồ sơ"'`, khẳng định ngay thiết bị đang ở Profile root (dù đang bị scrolled), không được coi là màn hình lạ.
