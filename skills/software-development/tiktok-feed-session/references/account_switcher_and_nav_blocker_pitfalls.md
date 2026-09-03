# Account Switcher & Navigation Blocker Pitfalls (Feed Session)

## 1. Tài khoản đã được chọn sẵn trong Switcher (`selected="true"`)
- **Hiện tượng:** Script mở bảng bottom sheet "Chuyển đổi tài khoản" (Switch account), thấy tài khoản mục tiêu và thực hiện tap vào tọa độ của tài khoản đó. Tuy nhiên bảng switcher không đóng lại, màn hình vẫn giữ nguyên bảng chọn tài khoản.
- **Nguyên nhân:** Trên TikTok Android, khi một tài khoản đã ở trạng thái active (có dấu tích đỏ ✔, XML có thuộc tính `selected="true"` hoặc `checked="true"`), việc tap lại vào chính node đó sẽ KHÔNG kích hoạt reload/đóng sheet như khi chuyển sang tài khoản khác.
- **Hệ quả:** Bảng modal switcher tiếp tục che toàn bộ Bottom Navigation Bar (thanh điều hướng đáy chứa các tab Home, Bạn bè, Hộp thư, Hồ sơ). Khi script chạy bước tiếp theo để tìm tab "Hồ sơ" (`profile`) thì XML dump không có node Profile -> văng lỗi `navigation target profile not found in XML`.
- **Giải pháp xử lý:**
  - Kiểm tra trạng thái `selected="true"` / `checked="true"` của node tài khoản mục tiêu trong switcher XML.
  - Nếu đã được tick chọn sẵn, thực hiện bấm nút **Đóng ("X")** trên header của switcher hoặc gửi phím **Back (keyevent 4)** để thoát khỏi modal thay vì tap lại vào row tài khoản.

## 2. Popup bảo mật "Tài khoản của bạn cần được cập nhật" (`account_update_prompt`)
- **Hiện tượng:** Sau khi chọn đổi tài khoản, TikTok hiển thị hộp thoại pop-up:
  - Tiêu đề: *"Tài khoản của bạn cần được cập nhật"*
  - Nội dung: *"Để tăng cường tính bảo mật, hãy liên kết số điện thoại hoặc địa chỉ email của bạn trước khi chuyển đổi tài khoản"*
  - Nút bấm: *"Liên kết số điện thoại hoặc email"* và *"Để sau"*.
- **Hệ quả:** Popup này nằm đè lên giao diện chính và chặn tương tác với Bottom Navigation Bar. Nếu script tiến hành điều hướng ngay về Profile mà không giải phóng popup, lệnh tìm nút Profile trong XML sẽ thất bại.
- **Giải pháp xử lý:**
  - Định vị nút *"Để sau"* (`dismiss_later_button` / bounds `[120,1271][960,1414]`) để đóng popup trước khi tiếp tục chuỗi điều hướng hoặc xác minh profile.
