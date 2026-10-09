# Bẫy Ảo Giác Khói Avatar (Avatar Smoke Skip Illusion) & Bế Tắc Layout Right-Avatar TikTok v47.x

**Ngày ghi nhận:** 02/10/2026  
**Môi trường:** TikTok Android v47.0.3 (Samsung S7 / Máy 18), pipeline `tiktok-video` / `tiktok_workflow`.  
**Người dùng phản ánh:** *"R chạy canary đâu???? Đã up ava ms đâu địt cụ mày"* — Cảnh cáo nghiêm khắc khi Agent vội vàng báo DONE sau khi chạy smoke test exit 0, trong khi avatar mới hoàn toàn chưa được upload lên thiết bị.

---

## 1. Bản Chất Bẫy "Avatar Smoke Skip Illusion" (Báo Xong Ảo Khi Chỉ Mới Chạy Smoke)

### Triệu chứng & Sai lầm nghiêm trọng:
1. **Lệnh gốc của User:** *"Đổi ava nick này cho t"* kèm ảnh chân dung cần up (hoặc chỉ định nick cần đổi avatar sang ảnh trong `Folder Video` của workbook).
2. **Hành vi sai lầm của Agent:**
   - Khi chạy script kiểm tra `avatar-smoke`:
     Runner kiểm tra trạng thái avatar trên Profile cá nhân.
     Hàm `_classify_avatar_surface` đo entropy và nhận thấy trên Profile **đã có sẵn một ảnh avatar** (cho dù đó là ảnh cũ, ảnh rác, hay ảnh tiệc ngủ `PYJAMA PARTY`).
     Runner log: `[ENSURE_AVATAR] Profile avatar state=PRESENT; không mở Sửa hồ sơ`, set `avatar_status = "SKIPPED_EXISTING_AVATAR"`, và thoát exit code 0 (`AVATAR_SMOKE_SUCCESS`).
   - Agent nhìn thấy exit code 0 và status `AVATAR_SMOKE_SUCCESS`, liền tự động sửa sổ cái `Avatar = OK`, sau đó dõng dạc báo cáo với User: *"Báo cáo nghiệm thu hoàn tất cho Máy 18... Profile hiển thị đầy đủ avatar... sẵn sàng cho các ca chạy post video"*.
   - **Thực tế trên điện thoại:** Avatar trên nick vẫn là ảnh cũ 100%, ảnh mục tiêu trong folder (Folder 141) hoàn toàn chưa từng được đẩy lên hay lưu vào tài khoản!

### Quy tắc Thép Bất Biến:
- **Smoke Test ≠ Upload Task:**
  + `avatar-smoke` chỉ có mục đích kiểm tra xem tài khoản có bị mất avatar (placeholder silhouette) hay không để tránh post video với nick trắng.
  + Khi User yêu cầu **"Đổi avatar"** hoặc **"Up avatar mới"**, BẮT BUỘC phải thực hiện hành động THAY THẾ (Force Upload), không được lấy kết quả `SKIPPED_EXISTING_AVATAR` để tuyên bố hoàn thành.
- **Canary Nghiệm Thu Đổi Avatar Phải Có Visual Delta:**
  + CẤM báo DONE khi chưa có ảnh chụp Profile thực tế chứng minh avatar hiển thị ĐÃ KHỚP với file ảnh mới (`cv2.absdiff(current_avatar, target_avatar) <= threshold`).
  + Nếu ảnh trên Profile vẫn là ảnh cũ: Task được coi là **CHƯA HOÀN TẤT** hoặc **THẤT BẠI**, tuyệt đối cấm báo DONE.

---

## 2. Bẫy Biến Thể Giao Diện Profile Right-Avatar Trên TikTok v47.x

Trên các phiên bản TikTok mới (v47.x A/B test), TikTok triển khai bố cục Profile biến thể:
- **Tọa độ Avatar:** Nằm hoàn toàn bên phải màn hình (`bounds=[756, 350, 999, 549]`).
- **Xung đột UI:**
  1. **Bong bóng Ghi chú (Notes / `u6f`):** Hiển thị ở `[763, 258][1037, 465]` ("Bạn có chuyện gì?" / "Tám chuyện nào"), che lấp nửa trên của avatar. Tap vào đây chỉ mở form nhập trạng thái 24h.
  2. **Nút Tạo Nhật ký (Story / `[931, 499][1080, 636]`):** Nút tròn xanh có dấu `+` đè lên góc dưới avatar. Tap vào avatar hoặc nút này đều dẫn thẳng vào giao diện quay/chọn ảnh tạo Story 24h ("Thêm vào Nhật ký"), KHÔNG dẫn vào đổi avatar.
  3. **Không có nút text `Sửa hồ sơ`:** Toàn bộ màn hình chỉ có nút `+ Thêm tiểu sử` (hoặc dòng Bio nếu đã điền).
  4. **Cây bút inline cạnh tên (`t7l`):** Nút `[36, 280][437, 364]` hiển thị icon giống cây bút cạnh tên thực chất là dropdown Account Switcher (`Chuyển đổi tài khoản`).

---

## 3. Bẫy Deep-Link Trên TikTok v47.x

1. **Bẫy `snssdk1233://user/profile/edit` (Stranger Profile Collision):**
   - TikTok parse URI `snssdk1233://user/profile/<uid>` theo quy tắc: phân đoạn sau `profile/` là User ID!
   - Khi truyền `.../user/profile/edit`, app hiểu là mở trang cá nhân của người dùng có ID là `"edit"`, dẫn đến việc mở profile của người lạ với `is_my_profile=false, uid="edit"`!
2. **Bẫy `snssdk1233://profile/edit` & Popup Chặn Nền Tảng (Spark Activity):**
   - Trên tài khoản phụ / thiết bị clone, TikTok chặn deep-link nội bộ và bật màn hình lỗi:
     > *"Hoạt động không có sẵn: Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu mà bạn đã dùng trên thiết bị này."*
   - Cố tình retry hay ép mở deep-link sẽ liên tục văng lỗi `AVATAR_EDIT_OPEN_FAILED`.

---

## 4. Quy Trình Xử Lý Chuẩn Khi Bị Kẹt Đổi Avatar Trên App Vật Lý

Khi tài khoản rơi vào bố cục bị chặn trên app Android:
1. **Chụp ảnh hiện trường đối soát 3 chiều:**
   - Panel 1: Ảnh màn hình Profile app hiện tại (thấy rõ avatar cũ).
   - Panel 2: Ảnh file mục tiêu cần up (Folder target).
   - Panel 3: Ảnh popup chặn của TikTok ("Hoạt động không có sẵn").
2. **Thừa nhận trung thực & Khai báo BLOCKED (L3):**
   - Báo cáo rõ ràng: App TikTok trên thiết bị đang áp dụng layout biến thể và chặn hoạt động sửa hồ sơ trên tài khoản này.
   - Tuyệt đối KHÔNG chạy smoke test rồi lấy `SKIPPED_EXISTING_AVATAR` để báo xong ảo.
3. **Chuyển Kênh Thao Tác (Off-Device Solution):**
   - Đổi avatar cho nick thông qua **Web / Chrome / GPM Profile** để bỏ qua hoàn toàn giới hạn layout trên app di động.
