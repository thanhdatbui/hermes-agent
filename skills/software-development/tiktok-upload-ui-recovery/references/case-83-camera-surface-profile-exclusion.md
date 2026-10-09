# Case 83: Phân Biệt Camera Surface Với Profile Root & Feed Root (Chống Tap Mù Video Tile)

## 1. Bản Chất Sự Cố (Root Cause)
Khi đăng video TikTok, nếu Camera mở ở chế độ Template hoặc bị lỗi và người dùng/hệ thống dismiss template hoặc bấm Back, màn hình TikTok rơi về màn hình Profile (Hồ sơ) hoặc Feed (Trang chủ).
- **Lỗ hổng phân loại UI:**
  - Header của màn hình Profile có icon chụp ảnh/story với thuộc tính `content-desc="Camera"`.
  - Tab danh sách video của Profile có text chứa `"Đăng"` hoặc `"Đã đăng"`.
  - Hàm kiểm tra camera (`_is_camera_surface_xml`) nếu chỉ match chuỗi con `"camera"`, `"đăng"`, `"tạo"` sẽ **nhận nhầm Profile root là Camera**.
- **Hệ quả dây chuyền (Cascade Failure):**
  - Hệ thống tưởng nhầm đang ở Camera nên gọi `_tap_visual_camera_upload_entry`.
  - Hàm visual upload tính toán tọa độ alternative thumbnail ở góc dưới trái `(156, 1574)` và tap mù vào đó.
  - Trên Profile grid, tọa độ `(156, 1574)` tap trúng video tile đầu tiên của kênh, mở trang xem chi tiết video cá nhân (**Profile video playback surface**).
  - Trang xem video cá nhân có nút cài đặt quyền riêng tư (`:id/sl0`), số lượt xem (`:id/view_entrance_text`), và nút back (`:id/bq7`).
  - Trang này không có nút tạo `+`, dẫn đến fail-closed: `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`.
  - Dù có thoát bằng nút `bq7` về Profile, nếu `_is_camera_surface_xml` vẫn trả về `True` cho Profile, hệ thống sẽ tiếp tục tap lại `(156, 1574)`, tạo thành vòng lặp vô tận.

## 2. Quy Tắc Loại Trừ Bất Biến (Structural Invariants)

### A. Loại Trừ Profile Video Playback Surface
Màn hình xem video cá nhân có các dấu hiệu độc quyền:
- Nút riêng tư: `:id/sl0`, text `"Cài đặt quyền riêng tư"` / `"Privacy settings"`.
- Lối vào thống kê: `:id/view_entrance_text`, text `"lượt xem"` / `"views"`.
- Nút back: `:id/bq7`, `content-desc="Quay lại"`.
-> Nếu phát hiện, `_is_camera_surface_xml` PHẢI trả về `False`, đồng thời gọi recovery tap `bq7` (hoặc `adapter.back()`) để về Profile.

### B. Loại Trừ Thanh Điều Hướng Đáy Của Root Tabs (Bottom Navigation Bar)
- **Đặc trưng cốt lõi:** Khi Camera modal mở, thanh điều hướng đáy (Home, Cửa hàng, +, Hộp thư, Hồ sơ) **hoàn toàn bị ẩn** để nhường chỗ cho nút chụp/quay và chế độ camera.
- **Quy tắc vàng:** Nếu XML xuất hiện đồng thời:
  - Tab Trang chủ: `text="trang chủ"`, `content-desc="trang chủ"`, `text="home"`, hoặc `content-desc="home"`
  **VÀ**
  - Tab Hồ sơ: `text="hồ sơ"`, `content-desc="hồ sơ"`, `text="profile"`, hoặc `content-desc="profile"`
  -> **ĐÂY CHẮC CHẮN LÀ ROOT NAVIGATION TAB (Feed hoặc Profile), TUYỆT ĐỐI KHÔNG PHẢI CAMERA** -> `return False`.

### C. Loại Trừ Profile Root Markers
Nếu XML chứa các nhãn đặc thù của Profile:
- `"sửa hồ sơ"`, `"chỉnh sửa hồ sơ"`, `"edit profile"`, `"chia sẻ hồ sơ"`, `"thêm tiểu sử"`, `"hoàn tất hồ sơ"`, `"complete profile"`, `"add bio"`, `"menu hồ sơ"`, `"profile menu"`, `:id/ny0`, `"/ny0"`
-> `return False`.

### D. Loại Trừ Feed Root
- Nếu XML chứa `"long_press_layout"` và bất kỳ nhãn feed nào (`"dành cho bạn"`, `"for you"`, `"đang follow"`, `"following"`) -> `return False`.

## 3. Luồng Phục Hồi Chuẩn Sau Khi Về Profile / Feed
Khi đã loại trừ Profile/Feed khỏi camera surface:
1. Outer flow (`_handle_video_pick` hoặc `_recover_video_pick_create_entry`) không còn cố tap thumbnail mù.
2. Hệ thống tìm nút create `+` ở đáy màn hình (`_find_bounded_create_button` với vùng `center_x` 40%-60%, `center_y >= 88%` và nhãn `+`, `quay`, `tạo`, `create`).
3. Tap vào nút create `+` để kích hoạt lại Camera một cách sạch sẽ.
4. Sau đó `_wait_for_verified_media_picker_after_recovery` sẽ tiếp quản để vào Media Picker.
