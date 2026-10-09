# TikTok Account Switcher Sticky Header Pattern

## Nguyên tắc cốt lõi
1. **CẤM TUYỆT ĐỐI BẤM VÀO AVATAR**: Chuyển nick / mở account switcher không bao giờ bấm vào avatar.
2. **Cơ chế Sticky Header chuẩn**:
   - Khi vào trang Profile, tên/ID ban đầu nằm ở vị trí thông thường và có thể lẫn với các gợi ý hoặc bio.
   - Bắt buộc thực hiện thao tác vuốt cuộn Profile lên: `swipe 540 1100 540 600 250` (hoặc tương đương theo tỉ lệ màn hình).
   - Thao tác vuốt này sẽ ghim ID và Tên hiển thị lên thanh header cố định (sticky header) ở đỉnh màn hình chính giữa (`y` nhỏ nhất trong các candidates header).
   - Tap vào text tên hoặc ID tại header đã ghim để xổ danh sách tài khoản (bottom sheet switcher).
3. **Bộ lọc Candidates**:
   - Khi quét text vùng header, nếu có nhiều hơn 1 node (ví dụ tên hiển thị và text gợi ý/bio), ưu tiên chọn node có tọa độ `y` nhỏ nhất (`min(candidates, key=lambda c: c[2])`).
