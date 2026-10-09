# Fallback Account Switcher: Nhận diện & Xử lý Tài khoản Placeholder `user...`

## 1. Hiện tượng & Bản chất vấn đề
- Khi TikTok mở popup **Chuyển đổi tài khoản** (Account Switcher bottom sheet), một số tài khoản đã đăng nhập sẵn trên máy nhưng bị TikTok hiển thị sai tên thành dạng placeholder `user...` (ví dụ `user1196792370966`), do lag cache UI hoặc chưa đồng bộ tên người dùng từ máy chủ TikTok.
- Nếu script chỉ đối soát exact match với `expected_account` (ví dụ `stevemgjqec`), hàm tìm kiếm sẽ trả về `None`, dẫn đến lỗi sai:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
  hoặc kích hoạt thừa quy trình auto-reconcile / login lại trong khi nick thực chất đã nằm sẵn trên máy.

## 2. Quy trình Xử lý Chuẩn (Auto-Recovery)
1. **Quét tìm Exact Match trước:**
   Tìm theo `expected_account` chuẩn hóa. Nếu tìm thấy exact match -> tap chuyển ngay.
2. **Fallback Placeholder `user...` khi không thấy Exact Match:**
   - Dùng helper `_find_user_placeholder_switch_option(popup_xml)` quét các node TextView / view có text hoặc content-desc khớp regex `^user\d+$` (case-insensitive).
   - Kiểm tra toạ độ `bounds` và `center` hợp lệ.
   - Nếu có ứng viên `user...`, chọn ứng viên này, log action:
     `action="try_user_placeholder_account", extra={"placeholder_label": ..., "expected": ...}`
   - Tap chuyển vào tài khoản placeholder này.
3. **Verify lại danh tính thực tế tại trang Profile:**
   - Sau khi switch, script điều hướng vào trang cá nhân (Profile tab) và đọc username / display name thực tế qua `_read_profile_identity_with_add_phone_guard`.
   - Nếu username trên trang cá nhân khớp với `expected_account` (ví dụ `@stevemgjqec`) -> ghi nhận `profile matched account`, chuyển trạng thái `success`/`matched` và tiếp tục phiên nuôi acc (lướt feed).
   - Nếu không khớp -> lúc này mới ghi nhận mismatch thực sự và thực hiện retry / reconcile.
4. **Luôn Dismiss Modal Switcher trước khi chuyển luồng:**
   - Nếu sau các lần thử không tìm thấy hoặc sau khi kiểm tra không khớp, BẮT BUỘC gửi `input keyevent 4` (BACK) kèm log `dismiss_switcher_on_missing_account` để hạ bottom sheet switcher trước khi trigger login flow hoặc thoát session, tránh che khuất UI cho các lượt chạy sau.

## 3. Lưu ý Kỹ thuật Codebase
- Trong `automation_core.tiktok.account_switcher`: Package không có hàm `list_account_switch_options`. Khi bóc tách XML switcher, sử dụng `_nodes(xml_text)` hoặc duyệt trực tiếp XML để lấy node, sau đó bọc thành `UIElement` có đầy đủ `bounds`, `center`, `attrib`.
- Runner PowerShell `run-feed-session.ps1`: Chú ý cú pháp biến `${m}:` khi format chuỗi máy trong PowerShell để tránh lỗi `InvalidVariableReferenceWithDrive`.
