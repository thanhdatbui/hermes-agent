# Avatar Flow Drift vs Post Media Picker & Profile Screenshot Trap

## 1. Hiện Tượng (Symptom)
- Dàn máy farm (ví dụ: Máy 01, 02, 03) chạy flow đổi avatar (`post_evening_avatar_watchdog` hoặc `tiktok_workflow --avatar-smoke --force-avatar-upload`) nhưng trên màn hình lại dừng lại ở bộ chọn Thư viện (Gallery) có:
  - Header: `X | Gần đây v | Bản nháp`
  - Tiêu đề phụ: `"Chọn ảnh liên quan đến chủ đề"`
  - Tab: `Tất cả | Video | Ảnh` (Tab "Ảnh" đang chọn)
  - Danh sách ảnh: Ô đầu tiên là Camera, ô thứ hai là **ảnh chụp màn hình Profile của chính account trong máy**, kèm nút `Chọn nhiều` và `Tiếp`.

## 2. Nguyên Nhân Kép (Dual Root Cause)
1. **Lệch Flow UI (UI Drift sang MvChoosePhotoActivity):**
   - Script bị click lệch tọa độ hoặc nhầm selector (bấm vào icon `+` tạo bài viết ở thanh điều hướng dưới cùng thay vì vào tab `Hồ sơ` -> `Sửa hồ sơ` -> `Thay đổi ảnh`).
   - Focus hiện tại trên thiết bị là:
     `com.ss.android.ugc.trill/com.ss.android.ugc.aweme.shortvideo.mvtemplate.choosemedia.MvChoosePhotoActivity`
   - Đây là activity **ĐĂNG BÀI / TẠO STORY / PHOTO POST**, hoàn toàn **KHÔNG PHẢI** flow đổi Avatar (`ProfileEditActivity`).
2. **Bẫy Gallery Screenshot (Gallery Indexing Trap):**
   - Trước khi upload, các watchdog (`inspect_machine`, `avatar_watchdog`, pre-flight check) chụp ảnh màn hình Profile bằng ADB screencap và lưu vào thư mục công khai (`/sdcard/DCIM/Screenshots`, `/sdcard/Pictures/Screenshots`).
   - Android MediaStore tự động quét (MediaScanner) và đưa ảnh này vào Thư viện.
   - Khi `MvChoosePhotoActivity` mở ra, danh sách media sắp xếp theo thời gian mới nhất (DESC). Ảnh chụp màn hình Profile vừa được tạo tức thì nên xuất hiện ở vị trí đầu tiên của tab `Ảnh`.

## 3. Quy Trình Chẩn Đoán O(1)
1. **Kiểm tra Focus:**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
   Nếu `Current Focus` là:
   - `...aweme.shortvideo.mvtemplate.choosemedia.MvChoosePhotoActivity`: Đang ở flow Đăng bài (Post Media Picker) -> **Lệch flow**.
   - `...aweme.profile.ui.ProfileEditActivity` hoặc sub-dialog: Đang ở đúng flow Avatar.
2. **Nhận diện UI trực quan:**
   - Flow Đăng bài: Có chữ `"Bản nháp"`, `"Chọn ảnh liên quan đến chủ đề"`, nút hồng `"Tiếp"`.
   - Flow Đổi avatar: Có viền crop tròn (`avatar_crop`), nút `"Lưu"` / `"Xác nhận"`.

## 4. Xử Lý Khẩn Cấp & Phòng Ngừa
- **Teardown khi lệch flow:** Nhấn nút Back (`input keyevent KEYCODE_BACK`) hoặc `am force-stop com.ss.android.ugc.trill` để hủy flow post nhầm, tuyệt đối không tap "Tiếp".
- **Cách ly Screenshot khỏi Gallery:** Khi chụp ảnh màn hình audit/evidence, lưu vào `/data/local/tmp/` hoặc đặt file `.nomedia` trong thư mục tạm trên Android để ngăn MediaScanner index ảnh vào Gallery.
- **Guard Focus trong Script:** Trước khi thực hiện tap chọn ảnh trong flow Avatar, script bắt buộc kiểm tra current activity: nếu phát hiện `MvChoosePhotoActivity`, hủy ngay lập tức (fail-safe abort).
