# Fallback Account Switcher: Nhận diện và Xử lý tài khoản dạng placeholder `user...`

## Bối cảnh & Nguyên nhân (Root Cause)
- Khi tài khoản mới đăng nhập hoặc TikTok bị lag cache/chưa đồng bộ tên hiển thị trong sheet Account Switcher, tài khoản có thể hiển thị dưới dạng placeholder username tự sinh của TikTok: `user...` (pattern: `^@?user\d+`, ví dụ: `user1196792370966`), thay vì username chính thức (ví dụ: `stevemgjqec`).
- **Hiện tượng lỗi:**
  - `_find_account_switch_option(popup_xml, expected)` chỉ tìm exact match tên tài khoản mục tiêu.
  - Khi không thấy exact match, flow kết luận thiếu tài khoản: `manual-needed:account-switcher-missing-expected`, sau đó dismiss switcher và chuyển sang bước reconcile auto-login hoặc fail máy, trong khi tài khoản thực chất đã có sẵn trên máy dưới tên placeholder `user...`.

## Quy tắc Fallback chuẩn
1. **Fallback candidate detection:**
   - Khi `_find_account_switch_option` không tìm thấy exact match của `expected`:
   - Quét qua danh sách các tài khoản trong switcher XML để tìm các candidate có username khớp pattern `^@?user\d+$`.
   - Lọc bỏ các nhãn hệ thống hoặc nút hành động (ví dụ `Add account`, `Log in`, ...).
2. **Thao tác Switch:**
   - Nếu có candidate `user...`, tap chọn candidate này để switch vào profile.
   - Ghi nhận log switch với action/reason rõ ràng (ví dụ: `fallback_tap_placeholder_user_account`).
3. **Verify Profile nghiêm ngặt:**
   - Sau khi TikTok hoàn tất chuyển tài khoản, đọc lại profile identity (`_read_profile_identity_with_add_phone_guard`).
   - Kiểm tra `username` hoặc `display_name` thực tế của profile có khớp với `expected_account` không.
   - **Thành công:** Nếu profile hiển thị đúng `expected_account`, ghi nhận switch thành công (`switched`) và tiếp tục luồng nuôi/swipe.
   - **Thất bại:** Nếu sau khi switch mà profile vẫn mismatch (vẫn là account khác không phải `expected`), coi như fallback không đúng, tiếp tục retry với attempt tiếp theo hoặc chuyển sang recovery login reconcile.
