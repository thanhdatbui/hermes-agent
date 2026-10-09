# Case: Camera "TẠO" Tab vs Dismissal Loop (Machine 39 & Samsung 1080x1920)

## 1. Hiện tượng (Symptom)
Khi thực hiện bước `VIDEO_PICK`:
- Sau khi tap nút `(+)` từ feed, TikTok mở giao diện tạo video.
- Script ghi nhận không tìm thấy XML upload node và kích hoạt visual fallback: tap thumbnail ở `(156, 1574)` hoặc `(945, 1593)`.
- Log xuất hiện cảnh báo lặp lại liên tục:
  ```text
  [WARNING] [CAMERA] Template surface opened instead of media picker; dismissing template surface
  [CAPCUT_TEMPLATE] Phát hiện màn hình template/hub; tiến hành dismiss
  [CAPCUT_TEMPLATE] Tapping top back/close button at (84, 204)
  [CAPCUT_TEMPLATE] Đã thoát màn template/hub; dismissed=True attempt=1/4
  [CAMERA] Switching to alternative thumbnail target (2/4): (945, 1593)
  ...
  Camera upload thumbnail tap did not open a verified gallery picker
  ```
- Dẫn đến **dismissal loop** và timeout fail cả workflow.

## 2. Bằng chứng hiện trường & Root Cause (Evidence First)
Phân tích ảnh chụp `video-pick-camera-surface.png` (kích thước 1080x1920) bằng WinRT OCR:
- **Header đỉnh (y=122..312):**
  - Text: `CREATE` / `TẠO`, `Video mới` (search bar).
  - Danh mục tabs: `Đề xuất` (x=37..150), `Bài hát lan truyền` (x=270..655), `Xu hướng` (x=721..926).
- **Body giữa màn hình (y=400..1750):**
  - Danh sách video template CapCut / TikTok hiển thị dạng feed: e.g. *"CỨ VỘI VÀNG"*, *"mưa đi mưa đừng rơi - 25,5K video • 2 clip"* (y=1073..1165), *"Nếu so sánh cậu ấy - 157,9K video • 1 clip"* (y=1287..1384).
  - Không có Shutter (nút chụp) và **không có nút Tải lên/Gallery**.
- **Thanh mode dưới đáy (y=1805..1839):**
  - `CAMERA`: `[x=217, y=1805, w=197, h=34]` (trọng tâm x~315)
  - `TẠO` (Active / Selected): `[x=494, y=1805, w=91, h=34]` (trọng tâm x~540)
  - `LIVE`: `[x=668, y=1805, w=93, h=34]`

### Cơ chế lỗi (Dismissal Loop):
1. TikTok sau khi ấn `(+)` tự động giữ hoặc mở tab **"TẠO"** (Templates Hub) thay vì **"CAMERA"**.
2. Script `state_machine.py` ngộ nhận đây là camera viewfinder nên gửi lệnh tap mù vào tọa độ thumbnail fallback `(156, 1574)` hoặc `(945, 1593)`.
3. Tọa độ này trúng ngay vào một video template card hoặc nút "Sử dụng mẫu", khiến TikTok mở giao diện template preview.
4. Logic bảo vệ `_is_capcut_template_surface` phát hiện đúng màn hình CapCut template và ấn Back/Close ở `(84, 204)`.
5. Sau khi Back, màn hình trở về tab **"TẠO"**. Script lại thử tọa độ thứ 2 `(945, 1593)` -> lại trúng template -> lại dismiss -> vòng lặp vô tận.

## 3. Tọa độ chuẩn & Giải pháp chuẩn hóa (Pattern)

### Tọa độ trên màn hình 1080x1920:
- **Tab `CAMERA` trên thanh Mode Bar đáy:** `[x=315, y=1820]`.
- **Nút Shutter (trung tâm):** `[x=540, y=1590]`.
- **Nút Tải lên / Gallery (bên phải Shutter):** `[x=945, y=1590]`.
- **Nút Hiệu ứng / Effects (bên trái Shutter):** `[x=156, y=1590]`.

### Quy tắc xử lý trong `state_machine.py`:
1. **Kiểm tra Marker của Template Hub trước khi tap fallback:**
   - Nếu màn hình chứa các chuỗi: `"Đề xuất"`, `"Bài hát lan truyền"`, `"Xu hướng"`, `"Video mới"` hoặc node `TẠO` đang được chọn (`selected=true`).
   - **TUYỆT ĐỐI KHÔNG** tap tọa độ thumbnail `(156, 1574)` hay `(945, 1593)`.
2. **Chuyển về Camera Mode:**
   - Tap vào tab `CAMERA` tại `(315, 1820)` (hoặc tìm node text `CAMERA`/`Máy ảnh`).
   - Chờ 1.5s để UI animate chuyển sang camera viewfinder.
3. **Mở Gallery:**
   - Sau khi xác nhận đã ở camera viewfinder (thấy shutter hoặc hết marker template), mới thực hiện tap nút Gallery tại `(945, 1590)`.
