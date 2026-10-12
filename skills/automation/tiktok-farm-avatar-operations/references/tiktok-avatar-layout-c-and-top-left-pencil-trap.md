# TikTok Avatar: Layout C & Top-Left Pencil False-Positive vs Add-Friend Button (2026-10-12)

## Context & Phenomenon
Trên TikTok v47.0.3+ (ví dụ Máy 21, tài khoản `@cao.m.phng7`), giao diện profile xuất hiện biến thể Layout C:
1. **Avatar lệch phải**: `[708,300][1080,636]` kèm bong bóng Note 24h ("Bạn có tin vui?", "Thì thầm to nhỏ", "Tám chuyện nào").
2. **Không có nút "Sửa hồ sơ" ở giữa**: Chỉ có nút "Thêm tiểu sử" hoặc tag danh mục.
3. **Header góc trên bên trái**: Có icon "Thêm bạn bè" (Add Friend) với resource-id `zz5` / `pwb` hoặc content-desc "Thêm bạn bè" tại `[126,96][228,204]`. Bên cạnh là icon `[24,96][126,204]`.
4. **Header góc trên bên trái thực sự**: Icon cây bút chì (Edit profile) chuẩn của TikTok nằm ở tọa độ `(75, 150)`.

---

## 1. Pitfall: TopLeftPencilLayout False-Positive
- **Lỗi**: `TopLeftPencilLayout.matches` trước đây chỉ kiểm tra kích thước bounds của icon góc trên trái mà không loại trừ icon Add Friend (`zz5`/`pwb`).
- Khi gặp màn hình có icon `zz5`, workflow nhận nhầm đây là layout có nút bút chì và tap nhầm vào vị trí của nút Thêm bạn bè hoặc tap vào avatar lệch phải.
- Khi tap vào avatar lệch phải đang có Note bubble, TikTok mở ra pop-up Story 24h (*"Hiển thị với follower trong 24 giờ"*), dẫn đến crash `[AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên`.

### Cách xử lý:
1. Trong `top_left_pencil.py`, bổ sung kiểm tra:
   ```python
   if tree.has_text("sửa hồ sơ", "chỉnh sửa hồ sơ", "edit profile") or tree.has_rid("zz5", "pwb"):
       return False
   ```
2. Trong `state_machine.py`, nếu deeplink `snssdk1233://profile/edit` được gọi, kiểm tra xem màn hình Sửa hồ sơ đã mở chưa trước khi fallback:
   ```python
   current = adapter.dump_ui()
   if any(k in (current or "") for k in ("Thay đổi ảnh", "Change photo", "Sửa hồ sơ", "Edit profile")):
       return True
   ```

---

## 2. Toạ độ chuẩn mở Sửa hồ sơ & Luồng thay avatar trên Layout C
Khi ở màn hình Profile của Layout C:
1. **Mở màn hình Sửa hồ sơ**:
   - Tap vào icon bút chì góc trên bên trái tại tọa độ `(75, 150)`.
   - Màn hình sẽ chuyển sang `UserProfileHostActivity` (Sửa hồ sơ) với các mục: *Thay đổi ảnh*, *Tên*, *Tên người dùng*, *Tiểu sử*.
2. **Mở Bottom Sheet**:
   - Tap vào *"Thay đổi ảnh"* tại `(540, 580)`.
   - Bottom Sheet hiện lên với 2 lựa chọn: *Chụp ảnh*, *Tải ảnh lên*.
3. **Mở Photo Picker**:
   - Tap vào *"Tải ảnh lên"* tại `(300, 1637)`.
4. **Chọn ảnh avatar mới**:
   - Trước khi vào Picker, push ảnh vào `/sdcard/DCIM/Camera/` và `/sdcard/Pictures/` rồi phát broadcast `MEDIA_SCANNER_SCAN_FILE` để ảnh mới nằm ở ô đầu tiên (hàng 1, cột 1).
   - **Checkbox Trap**: Tap vào radio circle / checkbox của ô đầu tiên tại `(225, 290)` (tránh tap vào giữa ảnh bị xem trước).
   - Tap nút *"Tiếp"* tại `(912, 1844)`.
5. **Crop & Lưu avatar**:
   - Màn hình Crop tròn xuất hiện.
   - Tap nút *"Lưu"* (Save) ở dưới đáy màn hình tại `(790, 1794)` và đợi 6s để TikTok lưu ảnh lên server.
   - Back về Profile và kiểm tra lại avatar bằng mắt (Gate 6).

---

## 3. Kỷ luật điều phối & Chống treo phiên (Anti-Hang Discipline)
- **Tín hiệu bức xúc từ User ("cmm treo hơn 1h r")**: Do Coordinator mất thời gian chần chừ, phân tích vòng vo mà không dứt khoát thực thi hoặc tự đóng băng khi gặp lỗi layout mới.
- **Quy tắc dứt điểm**:
  1. Khi đã xác định được exact coordinates và flow thực thi (như đã test trên Máy 71 / Máy 22), lập tức thực thi luồng nạp ảnh -> tap -> kiểm chứng visual.
  2. Không để session bị gián đoạn hoặc lặp lại các lệnh inspect không cần thiết khi device lock đã rảnh.
  3. Cập nhật ngay kết quả vào Excel (`Tik<N>.xlsx`) và database (`avatar_replace_queue` trong `tiktok_tracker.db` với cột `may = <N>`), giải phóng lock và đưa máy về trạng thái `KEYCODE_SLEEP`.
