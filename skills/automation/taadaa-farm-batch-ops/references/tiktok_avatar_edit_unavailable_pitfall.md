

---

## 23. Bẫy Popup "Hoạt Động Không Có Sẵn / Tài Khoản Ban Đầu" Khi Đổi Avatar & Chống Giành Lock Retry Mù (Incident 2026-10-02)

### 23.1. Hiện Tượng & Ngộ Nhận Tranh Chấp Lock
- Khi chạy đổi avatar cho tài khoản TikTok phụ trên thiết bị vật lý, runner liên tục báo lỗi:
  `[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở`
- Runner nhả lock và dọn về Home sau 1 lần thử thất bại.
- **Ngộ nhận thường gặp:** Người vận hành hoặc agent tưởng nhầm là do tranh chấp thiết bị hoặc chưa giành lại lock, dẫn đến chỉ đạo: *"Ủa phải giành lock lại chạy chứ"*.

### 23.2. Căn Nguyên Gốc Rễ: Cơ Chế Hạn Chế Nền Tảng Của TikTok (Platform Restriction)
1. **Bẫy Giới Hạn Secondary Account:**
   - Trên một máy điện thoại đăng nhập nhiều nick (tài khoản phụ), cơ chế bảo vệ của TikTok sẽ khóa hoặc giới hạn một số tính năng chỉnh sửa hồ sơ (edit profile, đổi avatar).
   - Nút "Sửa hồ sơ" và biểu tượng cây bút chì cạnh username bị ẩn hoàn toàn, chỉ còn hiển thị nút `+ Thêm tiểu sử` hoặc `Ban dang nghi gi...`.
2. **Popup Chặn Thao Tác:**
   - Khi runner hoặc người dùng cố gắng mở giao diện Sửa hồ sơ (bằng cách tap vào avatar circle, tap vùng tên, hoặc gọi deep-link `snssdk1233://profile/edit`), TikTok lập tức bật dialog hệ thống:
     > *"Hoạt động không có sẵn: Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
   - Popup này ngăn chặn mọi tương tác vào trang chỉnh sửa avatar.

### 23.3. Kỷ Luật Điều Phối & Chống Vòng Lặp Mù (Anti-Blind-Loop)
1. **CẤM TUYỆT ĐỐI Giành Lock Chạy Lặp Lại Mù Quáng:**
   - Nếu cố giành lock để ép chạy lại `avatar-smoke` hay `run_tiktok_upload_avatar.ps1`, thiết bị sẽ rơi vào vòng lặp vô tận: *Vào app -> Vào profile -> Bị popup chặn -> Timeout -> Thoát*. Tác vụ sẽ bị kéo dài hàng giờ vô ích mà không đổi được avatar.
2. **Quy Trình Xử Lý & Nghiệm Thu Bằng Chứng (Visual Evidence Invariant):**
   - Chụp ngay ảnh màn hình live của popup lỗi.
   - Gửi ảnh bằng chứng `MEDIA:<screenshot>` cho User để giải thích rõ nguyên nhân khách quan.
   - Phân loại rõ ràng vào nhóm **LỖI NỀN TẢNG (Platform Limit)**, không tính vào lỗi script hay circuit breaker.
3. **Hai Phương Án Khắc Phục:**
   - **Phương án 1 (Gỡ cờ trên máy):** Sử dụng Account Switcher chuyển tạm về tài khoản gốc (tài khoản ban đầu được tạo/đăng nhập đầu tiên trên máy) để giải phóng cờ hạn chế thiết bị của TikTok, sau đó switch lại nick mục tiêu để cập nhật avatar.
   - **Phương án 2 (Bỏ qua máy app):** Đăng nhập nick trên trình duyệt web (TikTok Web / TikTok Studio) bằng email/mật khẩu hoặc cookie để upload ảnh đại diện trực tiếp, tránh hoàn toàn bẫy giao diện của app mobile.
