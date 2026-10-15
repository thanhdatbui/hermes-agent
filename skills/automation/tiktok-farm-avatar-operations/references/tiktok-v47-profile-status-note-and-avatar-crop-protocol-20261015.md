# TikTok v47.0.3 Profile Layout Drift, Status Note Overlap & Avatar Replacement Protocol (15/10/2026)

## 1. Hiện Tượng & Cảnh Báo Hiện Trường
- **Triệu chứng:** Operator báo lỗi *"Là sao mày có đổi ava đâu"* kèm ảnh chụp màn hình avatar vẫn là ảnh cũ dù script báo `Exit code 0`.
- **Nguyên nhân gốc rễ (Layout Drift trên TikTok v47.0.3):**
  1. Trên TikTok v47, header trang Profile có layout bất đối xứng: Avatar nằm bên phải (`bounds: [708,246][1080,636]`), Tên và Follower nằm bên trái.
  2. **Bẫy Status Note:** Vòng tròn avatar bị một bong bóng Status Note ("Trà hay cà phê?", "Bạn có tin vui?") đè lên nửa trên từ $y=258$ đến $y=465$ (`com.ss.android.ugc.trill:id/u6f`). Tap vào nửa trên sẽ bật bàn phím gõ Note trạng thái!
  3. **Bẫy Story Button:** Nửa dưới bên phải avatar có nút `+` xanh "Tạo một Nhật ký" (`[931,499][1080,636]`). Tap vào đây sẽ mở camera/story picker!
  4. Nút `Sửa hồ sơ` dạng chữ nhật xám ở giữa màn hình bị ẩn hoàn toàn khi tài khoản có status note hoặc chưa cuộn.
  5. Script tap tọa độ cũ `(362, 481)` hoặc `(540, 430)` bị tap hụt ra ngoài hoặc dính vào Note status.

---

## 2. Quy Trình Điều Hướng Chuẩn Xác 100% Vào "Sửa Hồ Sơ" Trên TikTok v47

### Bước 1: Mở màn hình Sửa Hồ Sơ qua Icon Bút Chì Góc Trái
- Trên thanh header của Profile TikTok v47, luôn có icon cây bút chì ở góc trên bên trái:
  - `class: android.widget.ImageView`
  - `bounds: [24,96][126,204]`
- **Tọa độ tap chuẩn:** `(75, 150)`.
- Tap vào `(75, 150)` lập tức mở trực tiếp màn hình **"Sửa hồ sơ"** (`com.ss.android.ugc.trill:id/title` = "Sửa hồ sơ") mà không bị bất kỳ bong bóng note hay story nào cản trở!

### Bước 2: Kịch Bản Thay Đổi Ảnh Đại Diện
1. Trong màn hình **Sửa hồ sơ**:
   - Tap nút **"Thay đổi ảnh"** tại tọa độ `(540, 580)`.
2. Bottom sheet hiện lên ("Chụp ảnh", "Tải ảnh lên", "Xem ảnh"):
   - Tap **"Tải ảnh lên"** tại tọa độ `(540, 1637)`.
3. Photo Picker hệ thống/TikTok mở ra:
   - Tap vào tile ảnh mới nhất (vừa push lên và scan MediaStore) tại `(215, 276)`.
   - Tap nút **"Tiếp"** ở góc dưới bên phải tại `(1000, 1850)`.
4. Màn hình **Cắt / Crop**:
   - Tap nút **"Lưu"** tại tọa độ `(792, 1794)` (bounds: `[552,1728][1032,1860]`).
5. Chờ 5–6 giây để ảnh upload lên CDN máy chủ TikTok.
6. Nhấn nút Back góc trên trái `(84, 78)` hoặc `keyevent 4` để quay về Profile.

---

## 3. Nghiệm Thu Thị Giác Độc Lập (Gate 6 Invariant)
- **CẤM TUYỆT ĐỐI** báo xong chỉ dựa vào exit code của script.
- Bắt buộc chụp ảnh màn hình Profile (`dev.exec_out(["screencap", "-p"])`), crop vùng avatar `[708, 300, 1080, 636]` và chạy:
  1. **Haar Cascade Face Detection:** Xác nhận nhận diện đúng $\ge 1$ khuôn mặt người trong crop avatar.
  2. **RGB Profile Delta:** Xác nhận mean RGB của crop avatar khớp với ảnh chân dung nguồn, khác biệt hoàn toàn với ảnh cũ.
  3. Soi mắt qua `browser_vision` kiểm tra màn hình sáng rõ trước khi gửi thẻ `MEDIA:`.
