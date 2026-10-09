# Profile Video Playback Surface Recovery & Profile Root Misidentification

## Bối cảnh & Hiện tượng
Khi điều hướng từ Profile sang Creator / Media Picker trong `VIDEO_PICK`:
1. **Nhận nhầm Profile làm Camera:** Màn hình Profile của TikTok có thể bị nhận nhầm là Camera nếu logic nhận diện camera quá lỏng lẻo (không loại trừ Profile root markers).
2. **Tap nhầm vào Video Tile trong Profile Grid:** Khi cố gắng tap vào vùng tải lên (upload thumbnail) của camera giả định, tọa độ tap vô tình rơi trúng một video thumbnail trên lưới video cá nhân của Profile.
3. **Mở màn hình xem chi tiết video cá nhân (Profile Video Playback Surface):** TikTok chuyển sang màn hình phát video của chính tài khoản đó (khác với Feed công khai).

## Đặc trưng nhận diện XML (Profile Video Playback)
- **Nút Cài đặt quyền riêng tư:** `resource-id` chứa `:id/sl0` hoặc `/sl0`, text/desc `Cài đặt quyền riêng tư` / `Privacy settings`.
- **Lối vào thống kê lượt xem:** `resource-id` chứa `view_entrance_text` / `view_entrance`, text/desc `lượt xem` / `views`.
- **Nút Back quay lại profile:** `resource-id` chứa `:id/bq7` hoặc `/bq7`, desc `Quay lại` / `Back` (nằm ở top bar, bounds `top <= 400`).

## Giải pháp & Quy trình Recovery
1. **Chặn nhận diện sai (`_is_camera_surface_xml`):**
   - Loại trừ nếu là `_is_profile_video_playback_surface`.
   - Loại trừ Profile root markers: `sửa hồ sơ`, `chỉnh sửa hồ sơ`, `edit profile`, `chia sẻ hồ sơ`, `thêm tiểu sử`, `hoàn tất hồ sơ`, `menu hồ sơ`, `:id/ny0`.
   - Loại trừ Bottom Nav Bar đồng thời có `Trang chủ` (Home) và `Hồ sơ` (Profile).
   - Loại trừ Feed root (`long_press_layout` + `dành cho bạn` / `for you` / `đang follow`).

2. **Thoát màn hình video cá nhân (`_recover_profile_video_playback_surface`):**
   - Tìm nút back `:id/bq7` ở `top <= 400` và tap trực tiếp.
   - Nếu không tìm thấy node `:id/bq7`, fallback gọi `adapter.back()`.
   - Chờ UI ổn định (`time.sleep(1.2)`) trước khi dump lại XML để điều hướng lại về Camera/Picker.

3. **Tích hợp vào các điểm retry của StateMachine:**
   - Trong `_tap_visual_camera_upload_entry`: kiểm tra sau khi dismiss template hoặc sau mỗi lần tap alternative thumbnail. Nếu rơi vào playback surface, lập tức recover và trả về `False` để luồng ngoài định hướng lại.
   - Trong `_execute_video_pick`: trước khi mở camera/picker, nếu phát hiện playback surface thì gọi recover ngay.
   - Trong `_probe_or_recover_video_pick_create_entry`: kiểm tra `recaptured_xml` sau khi dismiss template hoặc sau khi tap upload thumbnail.
