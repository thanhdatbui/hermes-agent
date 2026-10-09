# TikTok Avatar Edit Restriction & UI Traps (AVATAR_EDIT_OPEN_FAILED)

## 1. Triệu chứng & Mã lỗi
- `AVATAR_EDIT_OPEN_FAILED`: ENSURE_AVATAR không thể mở màn hình Sửa hồ sơ / Edit Profile.
- Log xuất hiện: `Các nhánh profile không mở; thử fallback deep-link cuối` -> `AVATAR_EDIT_OPEN_FAILED`.
- Trên giao diện Profile máy thật:
  - Hoàn toàn KHÔNG có nút "Sửa hồ sơ" (`edit_profile`, `p46`, `toy`, text "Sửa hồ sơ").
  - Nút bên dưới follower count chỉ có: `+ Thêm tiểu sử` (`t3z`).
  - Phía trên avatar góc phải có text `Bạn đang nghĩ gì...` (`u6f`) và icon `+` màu xanh (`Tạo một Nhật ký` / Story, bounds `[931,499][1080,636]`).

## 2. Bẫy giao diện & Cấm bấm mò (Anti-Blind-Tap Invariant)
- **Bẫy nút Bio (`t3z`)**: Nút `+ Thêm tiểu sử` mở modal nhập Text Bio (chỉ có ô text và nút Lưu), KHÔNG PHẢI màn hình Sửa hồ sơ/đổi avatar.
- **Bẫy nút Story (`[931,499][1080,636]`)**: Icon `+` xanh trên avatar là nút tạo Story 24h, tap vào sẽ mở Camera/Thư viện đăng story chứ không phải đổi avatar.
- **Bẫy đổi nick qua Header (`t7l`)**: Tên hiển thị trên đỉnh (`t7l` / `com.ss.android.ugc.trill:id/t7l`) khi tap vào sẽ mở bottom sheet **Chuyển đổi tài khoản (Account Switcher)**. TUYỆT ĐỐI CẤM tap vào vùng này khi đang up avatar, tránh switch nhầm sang nick khác của máy.
- **Quy tắc khi gặp Popup lạ**: BẮT BUỘC dùng `input keyevent 4` (Back) ngay lập tức để thoát về Profile/Feed. CẤM TUYỆT ĐỐI tap mò vào các vùng khác trên màn hình khi chưa xác định rõ element.

## 3. Lỗi nền tảng TikTok: Hạn chế tài khoản phụ (Spark Restriction)
- Khi gọi deep-link `snssdk1233://profile/edit` hoặc `snssdk1233://user/profile/edit` trên các tài khoản phụ (secondary account trong switcher), TikTok chặn mở `ProfileEditActivity` và kích hoạt `SparkActivity` với popup:
  > **"Hoạt động không có sẵn: Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."**
- **Bản chất**: Đây là cơ chế bảo vệ thiết bị vật lý của TikTok khi tài khoản không phải tài khoản đầu tiên đăng ký/đăng nhập trên máy.
- **Cách xử lý chuẩn**:
  1. Xác định ngay đây là **LỖI NỀN TẢNG (Platform Restriction)**, KHÔNG cố gắng retry deep-link hoặc tap mù trên app.
  2. Bấm `Back` thoát popup SparkActivity về lại Profile.
  3. Báo cáo User kèm ảnh đối soát 3 phía (Ảnh User yêu cầu vs Ảnh Pipeline Folder vs Ảnh hiện tại trên Profile máy).
  4. Đề xuất đổi avatar qua Web / TikTok Studio / Profile Web để bypass hạn chế trên app vật lý.
