# Pitfall: Bẫy "Hoạt động không có sẵn / Tài khoản ban đầu" khi Đổi Avatar TikTok

## 1. Hiện tượng & Triệu chứng
- Workflow chạy đổi avatar (`ENSURE_AVATAR` / `--avatar-smoke`) liên tục văng lỗi:
  `[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở`
- Tiến trình thoát (exit code 1) sau 1 attempts, nhả lock về Home.
- User có thể hiểu nhầm là lỗi tranh chấp lock và yêu cầu: *"Ủa phải giành lock lại chạy chứ"*.

## 2. Bản chất kỹ thuật & Căn nguyên gốc rễ (Root Cause)
- Đây là **LỖI NỀN TẢNG (Platform Restriction)** từ cơ chế an toàn chống spam của TikTok:
  - Khi một thiết bị vật lý đăng nhập nhiều tài khoản (secondary accounts), TikTok hạn chế một số tính năng chỉnh sửa hồ sơ trên tài khoản phụ.
  - Khi cố gắng mở màn hình sửa hồ sơ, tap vào avatar circle hoặc gọi deeplink `snssdk1233://profile/edit`, app hiển thị dialog:
    > *"Hoạt động không có sẵn: Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
  - Trên giao diện Profile, nút "Sửa hồ sơ" và icon bút chì bị ẩn hoàn toàn, chỉ còn nút `+ Thêm tiểu sử`.

## 3. Kỷ luật điều phối & Chống vòng lặp mù (Anti-Blind-Loop)
- **CẤM TUYỆT ĐỐI**: Giành lock để retry mù (`force-avatar-upload` / `avatar-smoke`) lặp đi lặp lại. Việc này sẽ khiến máy kẹt hàng giờ trong chu trình: *Mở app -> Feed -> Profile -> Bị popup chặn -> Timeout -> Thoát*.
- **QUY TRÌNH XỬ LÝ CHUẨN**:
  1. Chụp ảnh màn hình live và OCR kiểm chứng nội dung popup.
  2. Bắt buộc gửi bằng chứng thị giác `MEDIA:<screenshot_popup>` cho User/báo cáo.
  3. Phân loại rõ ràng là **Lỗi Nền Tảng (Platform Limit)**, KHÔNG tính vào lỗi script/circuit breaker.
  4. Hai hướng xử lý:
     - **Hướng 1 (Trên máy)**: Chuyển tạm về tài khoản gốc (tài khoản ban đầu của máy) trong account switcher để gỡ cờ hạn chế của thiết bị, sau đó switch lại nick cần đổi avatar.
     - **Hướng 2 (Bỏ qua máy)**: Đổi avatar trực tiếp thông qua TikTok Web / TikTok Studio nếu có cookie/mật khẩu, tránh hoàn toàn bẫy giao diện app điện thoại.
