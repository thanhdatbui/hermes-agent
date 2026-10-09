# Bẫy Giao Diện Profile & Nhận Diện Nút Sửa Hồ Sơ (A/B Testing Variants)

## Hiện Tượng Lỗi (AVATAR_EDIT_OPEN_FAILED)
Trên các phiên bản TikTok mới (v47.x+, ví dụ 47.0.3 trên Samsung farm), TikTok chia nhóm A/B testing giao diện Profile theo từng tài khoản:

1. **Giao diện A (Truyền thống)**:
   - Hiển thị nút bấm to dạng chữ: `Sửa hồ sơ` / `Chỉnh sửa hồ sơ` (`edit_profile`, `p46`, `toy`) hoặc nút icon bút chì tách riêng ở bên phải header `[750..950, 450..650]`.
   - Selector XML dễ bắt qua text hoặc resource-id.

2. **Giao diện B (Biến thể mới - A/B Test)**:
   - Hoàn toàn **KHÔNG có nút chữ "Sửa hồ sơ"** (chỉ có nút `+ Thêm tiểu sử` / `Add bio`).
   - Icon cây bút chì được vẽ lồng ghép ngay sau tên hiển thị của tài khoản (nằm trong vùng bounding box của node button `t7l` tại tọa độ khoảng `[36, 280][437, 364]`).
   - **Bẫy tương tác**: Bấm vào giữa node `t7l` sẽ kích hoạt mở sheet Chuyển đổi tài khoản (Account Switcher) chứ không mở Sửa hồ sơ! Phải tap chính xác vào tọa độ icon bút chì ở mép phải của cụm tên (hoặc xử lý fallback navigation phù hợp).

## Kỷ Luật Điều Tra & Báo Cáo Hiện Trường (Chống Võ Đoán)
- Khi script chạy văng lỗi `AVATAR_EDIT_OPEN_FAILED`:
  - BẮT BUỘC kiểm tra và trích xuất đúng artifact screenshot sinh ra từ chính lần chạy đó (`runs/<run_id>/profile-grid-*.png` hoặc `account-switcher-*.png`).
  - TUYỆT ĐỐI KHÔNG dùng ảnh chụp từ các thao tác probe thủ công trên nick khác/phiên khác (như pop-up "Hoạt động không có sẵn" khi bấm nhầm nick phụ) để báo cáo sai lệch nguyên nhân cho người dùng.
  - Phải gửi ảnh nguyên gốc màn hình thực tế của nick mục tiêu để đối soát chính xác cấu trúc nút bấm.
