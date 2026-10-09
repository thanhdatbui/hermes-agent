# Case 83: Profile Root Camera False-Positive & Profile Video Playback Recovery (2026-09-05)

## Bối cảnh & Hiện tượng (Máy 38, `ce06160685310f1c04`)
- **Triệu chứng:** Batch runner báo lỗi `upload_subprocess_nonzero` (exit code 1).
- **Log run:** `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`.
- **Hiện trường:** Màn hình máy bị kẹt tại trang xem chi tiết video cá nhân (`Profile video player`), có nút "Cài đặt quyền riêng tư" (`:id/sl0`), "lượt xem" (`:id/view_entrance_text`), và nút back `<` ở góc trên bên trái (`:id/bq7`).

## Nguyên nhân cốt lõi (Anti-Pattern)
1. **`_is_camera_surface_xml` nhận nhầm Profile root là Camera surface:**
   - Hàm kiểm tra chuỗi `content-desc="camera"` và `text="đăng"`.
   - Trên TikTok Profile layout mới:
     - Header Profile có icon shortcut chụp ảnh/story mang `content-desc="Camera"`.
     - Tab video đầu tiên của Profile có text `"Đăng"` hoặc `"Bài đăng"`.
   - Khi dismiss CapCut template hoặc back về, UI rơi về Profile root nhưng `_is_camera_surface_xml` trả về `True`.
2. **Tap mù thumbnail video (`_tap_visual_camera_upload_entry`):**
   - Tưởng lầm Profile là Camera, script chụp màn hình Profile và tap alternative thumbnail tại góc dưới trái `(156, 1574)`.
   - Tọa độ `(156, 1574)` tap trúng ngay video tile đầu tiên trong grid video cá nhân -> mở trang phát video chi tiết (`Profile video playback surface`).
3. **Kẹt vòng lặp không có nút Create (+):**
   - Trang xem video cá nhân không có nút (+) create control ở đáy màn hình.
   - `_find_bounded_create_button` không tìm thấy nút (+) -> kích hoạt `_recover_video_pick_create_entry` và fail-closed `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## Giải pháp chuẩn hóa (Case Fix)
1. **Bộ lọc loại trừ 3 tầng trong `_is_camera_surface_xml`:**
   - Loại trừ Profile playback surface (`_is_profile_video_playback_surface`).
   - Loại trừ Profile root markers: `"sửa hồ sơ"`, `"chỉnh sửa hồ sơ"`, `"edit profile"`, `"chia sẻ hồ sơ"`, `"thêm tiểu sử"`, `"hoàn tất hồ sơ"`, `":id/ny0"`.
   - Loại trừ Root Navigation Bar: khi xuất hiện đồng thời cả 2 tab `Trang chủ` và `Hồ sơ`.
   - Loại trừ Feed root: khi có `long_press_layout` và các tab Feed (`"dành cho bạn"`, `"đang follow"`).
2. **Tự động nhận diện và phục hồi Profile Video Player:**
   - `_is_profile_video_playback_surface`: Nhận diện `:id/sl0`, `:id/view_entrance_text`, `:id/bq7`.
   - `_recover_profile_video_playback_surface`: Tự động tap `:id/bq7` (hoặc semantic back) đưa UI về Profile/Feed.
3. **Gate XML re-dump sau dismiss template:**
   - Trong `_tap_visual_camera_upload_entry`, sau khi dismiss template, bắt buộc re-dump XML. Nếu không còn là camera surface thì dừng ngay việc tap alternative thumbnail.
