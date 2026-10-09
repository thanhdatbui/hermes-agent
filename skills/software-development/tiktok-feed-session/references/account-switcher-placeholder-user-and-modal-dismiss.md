# TikTok Account Switcher: Placeholder `user...` & Modal Dismiss Rules

## 1. Placeholder Username `user...` trong Account Switcher
- **Hiện tượng**: Trong menu "Chuyển đổi tài khoản" (Account Switcher) của TikTok trên farm máy, một số tài khoản có thể hiển thị dưới dạng placeholder dạng số như `user1196792370966` (regex `^user\d+`) thay vì username thật (`stevemgjqec`) do lag đồng bộ cache tên hoặc TikTok gán username tạm thời.
- **Quy tắc xử lý bắt buộc**:
  1. Khi tìm `expected_account` trong danh sách tài khoản của Switcher mà không thấy exact match:
     - **CẤM** vội vã đánh dấu `manual-needed:account-switcher-missing-expected` hay kích hoạt auto-login/reconcile ngay lập tức.
     - **BẮT BUỘC** quét danh sách switcher tìm các tài khoản dạng `^user\d+`.
  2. Nếu phát hiện option `user...`:
     - Bấm chọn (tap) option đó để switch tài khoản.
     - Sau khi switch, flow tiến hành kiểm tra trang cá nhân (Profile page) để verify identity thật của tài khoản.
     - Nếu trang Profile xác nhận đúng là tài khoản mục tiêu (`expected_account`), ghi nhận switch thành công và tiếp tục phiên nuôi bình thường.
     - Nếu sau khi switch mà Profile xác nhận không phải tài khoản mục tiêu, mới tiếp tục các bước fallback tiếp theo.

## 2. Dismiss Modal Account Switcher trước khi Recovery
- **Hiện tượng**: Modal Account Switcher là dạng bottom sheet che phủ màn hình TikTok. Nếu thoát luồng switch hoặc trigger auto-login recovery mà không hạ modal, giao diện sẽ bị kẹt bottom sheet che khuất các nút điều hướng.
- **Quy tắc xử lý bắt buộc**:
  - Khi xác nhận thiếu tài khoản hoặc không tìm thấy option phù hợp:
  - BẮT BUỘC gửi lệnh `input keyevent 4` (BACK) kèm log `dismiss_switcher_on_missing_account` để hạ modal Account Switcher trước khi gọi hàm recovery login (`_maybe_recover_missing_account_via_login`) hoặc trước khi exit.
  - Đảm bảo UI luôn ở trạng thái Profile/TikTok sạch sẽ trước khi chuyển giao luồng.
