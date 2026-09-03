# TikTok Login & Reconcile UI Fallbacks & Hotmail Blocker (Machine 4 - 2026-08-19)

## 1. Màn hình Auth Landing trên máy chưa có nick (Logged-out / Fresh state)
- **Hiện tượng**: Khi máy chưa có tài khoản nào đăng nhập, mở TikTok hoặc tap vào tab "Hồ sơ" sẽ kích hoạt popup bottom-sheet `I18nSignUpActivity` (có logo TikTok, ô nhập SĐT / email và các nút *"Tiếp tục với email/tên người dùng"*).
- **Vấn đề**: Hàm `is_auth_landing_screen(xml)` cũ chỉ nhận diện khi có chuỗi `"dang ky tiktok"` kèm `"ban da co tai khoan"`. Trên giao diện mới của TikTok (modal trượt đăng nhập), text hiển thị là `"dang nhap"` + `"tiep tuc voi email"` -> hàm cũ bỏ qua khiến `ensure_login_entry_screen` cố gắng mở dropdown tài khoản (`open_account_dropdown`) và bị kẹt lặp lại.
- **Xử lý**:
  - Cập nhật `is_auth_landing_screen`: chấp nhận cả `("dang nhap" in flat and "tiep tuc voi email" in flat)`.
  - Trong `ensure_login_entry_screen`: bọc `open_account_dropdown` trong `try/except` -> nếu fail nhưng UI rơi vào auth landing screen thì vào thẳng `choose_email_login`.

## 2. Lỗi Substring Match trên đoạn văn bản Điều Khoản Dịch Vụ (`find_node_in_xml` / `tap_next`)
- **Hiện tượng**: Dưới cùng của popup đăng nhập có đoạn văn bản dài: *"Bằng việc tiếp tục với tài khoản có vị trí tại Việt Nam, bạn đồng ý với Điều khoản Dịch vụ..."*. Do có chứa chữ *"tiếp tục"*, `node_has_target` khớp nhầm đoạn văn bản này thay vì nút *"Đăng nhập"* hoặc *"Tiếp tục"* thật. Khi click vào đoạn text này, TikTok mở sang WebView Điều khoản Dịch vụ (`Terms of Service`).
- **Xử lý**:
  - Nâng cấp `node_has_target`: nếu chuỗi text trong XML dài (> 50 ký tự), chỉ cho phép khớp exact hoặc bỏ qua substring ngắn.
  - Nâng cấp `find_node_in_xml`: ưu tiên các node khớp chính xác (`exact_matches`) trước khi lấy match_pool để chọn node clickable lớn nhất.

## 3. Kwarg Drift `preserve_current_screen` giữa `account_reconcile.py` và `tiktok_login_v1.py`
- **Hiện tượng**: `login_runner/account_reconcile.py` truyền kwarg `preserve_current_screen` vào `login_module.login_one_account(...)`, nhưng provider `Tiktok_Reg/tiktok_login_v1.py` chỉ nhận `(device_id, stt, account, take_ss=False, update_tracking=True)`. Điều này gây crash `TypeError: unexpected keyword argument 'preserve_current_screen'`.
- **Xử lý**: Dùng `inspect.signature(login_module.login_one_account)` kiểm tra trước khi truyền `preserve_current_screen`.

## 4. Trạng thái `OUTLOOK_APP_INBOX_NOT_VERIFIED` khi lấy OTP Hotmail
- **Hiện tượng**: Khi TikTok gửi mã xác nhận OTP về email Hotmail không có token Graph API (`HOTMAIL_TOKEN_LIST`), script chuyển sang app Outlook trên máy nhưng app Outlook đang ở màn hình Onboarding ("Thêm email tài khoản của bạn").
- **Xử lý**: Dừng lại với trạng thái `OUTLOOK_APP_INBOX_NOT_VERIFIED` và chạy luồng `flows/login_outlook_one_machine.py` từ repo `D:\Taadaa\Hotmail` để đăng nhập email trước khi tiếp tục flow TikTok login.
