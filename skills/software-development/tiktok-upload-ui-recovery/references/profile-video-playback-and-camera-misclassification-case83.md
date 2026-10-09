# Case 83 (05/09/2026): Nhận Nhầm Profile Root Là Camera Surface Và Kẹt Màn Hình Xem Video Cá Nhân (Profile Video Playback Surface) Khi Đăng Video TikTok (Sự Cố Máy 38)

## 1. Hiện tượng & Bối cảnh
- **Thiết bị:** Máy 38 (`ce06160685310f1c04`), nick `thy.dung1828`, workbook `Tik2.xlsx` row 39, video 27.
- **Triệu chứng:** Batch runner báo lỗi `upload_subprocess_nonzero` (exit code 1).
- **Log thực tế (`report.json`):**
  ```json
  {
    "status": "MANUAL_REVIEW",
    "reason": "[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control"
  }
  ```
- **Hiện trường màn hình thật:** Máy dừng tại màn hình xem chi tiết video đã đăng của kênh cá nhân (Profile video player), hiển thị:
  - Header: Nút quay lại (`:id/bq7`, `content-desc="Quay lại"`), thanh tìm kiếm (`:id/tv_search_sug_word`, "Tìm nội dung liên quan").
  - Body: Video cá nhân đang phát, sidebar tương tác (Tim, Bình luận, Yêu thích, Chia sẻ, Đĩa nhạc).
  - Footer: Thống kê lượt xem (`:id/view_entrance_text`, "358 lượt xem"), nút `Cài đặt quyền riêng tư` (`:id/sl0`).

---

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause)

### A. Lỗ hổng nhận diện Camera (`_is_camera_surface_xml`)
Hàm `_is_camera_surface_xml` kiểm tra các marker lỏng:
```python
return any(
    marker in folded
    for marker in (
        "video_record_new_scene_root",
        'text="camera"',
        'content-desc="camera"',
        'text="thêm âm thanh"',
        "phát live",
        "trung tâm live",
        "chuyển đổi camera",
        'text="đăng"',
        'text="tạo"',
        'text="live"',
    )
)
```
1. Trên giao diện Profile TikTok, thanh header có icon camera tạo tin/chụp ảnh mang `content-desc="Camera"` hoặc `content-desc="camera"`.
2. Tab video đầu tiên của Profile có text chứa từ khóa `"đăng"` (ví dụ `"Đã đăng"`, `"Bài đăng"`).
3. Do thiếu điều kiện loại trừ màn hình Profile/Feed, hàm `_is_camera_surface_xml` đánh giá màn hình Profile root thành `True` (nhận nhầm là màn hình Camera).

### B. Tap mù video tile trên lưới Profile
1. Khi Camera mở ở chế độ LIVE hoặc Template hub, hàm `_dismiss_capcut_template_surface` bấm nút thoát/back `(84, 150)` đưa UI thoát khỏi Camera về lại màn hình Profile.
2. Tại `_tap_visual_camera_upload_entry`, do `_is_camera_surface_xml` trả về `True` trên Profile, hàm tiến hành chụp ảnh Profile và tính toán tọa độ alternative thumbnail ở góc dưới bên trái `(156, 1574)`.
3. Trên màn hình Profile, tọa độ `(156, 1574)` rơi trúng vị trí video tile đầu tiên trong grid video của tài khoản. Việc tap vào đây kích hoạt phát video và mở ra màn hình chi tiết video cá nhân (`Profile video playback surface`).

### C. Vòng lặp kẹt vô tận (Infinite Trap)
1. Khi ở màn hình phát video, không có nút (+) create button nên flow không thể mở media picker.
2. Kể cả khi bấm nút quay lại (`:id/bq7`) để thoát về Profile root, hàm `_is_camera_surface_xml` lại tiếp tục nhận nhầm Profile là Camera và tiếp tục tap `(156, 1574)` lần 2, lần 3, lần 4.
3. Khi hết số lượt tap retry (`max_taps=4`), workflow fail-closed với exception `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.

---

## 3. Giải pháp Chuẩn (Standard Fix Pattern)

### 1. Nhận diện màn hình phát video cá nhân (`_is_profile_video_playback_surface`)
Xác thực sự xuất hiện của các UI element đặc thù (BẮT BUỘC dùng attribute-scoped matching để tránh false-positive):
- Nút cài đặt quyền riêng tư: `:id/sl0`, text `"Cài đặt quyền riêng tư"` hoặc `"Privacy settings"`.
- Thống kê lượt xem cá nhân: `:id/view_entrance_text` / `/view_entrance_text`, text `"lượt xem"` hoặc `'text="views"'` / `'content-desc="views"'`.
  *(⚠️ PITFALL ĐƯỢC PHÁT HIỆN TẠI PLAN-REVIEW GATE 1: Tuyệt đối KHÔNG dùng `"views" in lowered` vì từ "views" là substring của "viewpager", "viewholder", "overview"... Nếu màn hình Camera có viewpager và nút back, check substring "views" sẽ nhận nhầm Camera là video player! Phải dùng attribute-scoped `'text="views"'` hoặc `'content-desc="views"'`).*
- Nút back quay lại: `:id/bq7`, `content-desc="Quay lại"` / `content-desc="Back"`.

### 2. Phục hồi tự động (`_recover_profile_video_playback_surface`)
- Tìm node `:id/bq7` ở `top <= 400` và tap vào tâm node `(cx, cy)`.
- Fallback gọi semantic `adapter.back()`.
- Chờ 1.2s để UI ổn định trở lại Profile root hoặc Feed.

### 3. Khóa chặt bộ lọc `_is_camera_surface_xml`
Loại trừ triệt để các màn hình không phải Camera:
1. **Loại trừ Profile video player:**
   ```python
   if cls._is_profile_video_playback_surface(xml_text):
       return False
   ```
2. **Loại trừ Profile root:**
   Kiểm tra các marker đặc trưng của Profile: `"sửa hồ sơ"`, `"chỉnh sửa hồ sơ"`, `"edit profile"`, `"chia sẻ hồ sơ"`, `"thêm tiểu sử"`, `"menu hồ sơ"`, `"hoàn tất hồ sơ"`, `:id/ny0`.
   *(⚠️ Bỏ marker ngắn `"/ny0"` vì dễ match nhầm resource-id khác; chỉ dùng `":id/ny0"`).*
3. **Loại trừ Root Navigation Bar (Feed / Profile root tabs):**
   Khi Camera mở, thanh điều hướng đáy (Bottom Navigation Bar) bị ẩn hoàn toàn để nhường chỗ cho nút chụp và các chế độ quay.
   Nếu XML xuất hiện đồng thời tab điều hướng (`"trang chủ"` / `"home"`) VÀ (`"hồ sơ"` / `"profile"`), đây chắc chắn là giao diện chính (Feed hoặc Profile), KHÔNG PHẢI Camera:
   ```python
   has_home = any(m in folded for m in ('text="trang chủ"', 'content-desc="trang chủ"', 'text="home"', 'content-desc="home"'))
   has_profile = any(m in folded for m in ('text="hồ sơ"', 'content-desc="hồ sơ"', 'text="profile"', 'content-desc="profile"'))
   if has_home and has_profile:
       return False
   ```
4. **Loại trừ Feed root:**
   Kiểm tra `long_press_layout` và (`"dành cho bạn"`, `"for you"`, `"đang follow"`, `'text="following"'`, `'content-desc="following"'`).
   *(⚠️ Tránh bare substring `"following"` vì dễ dính `following_count` hay attributes khác).*

### 4. Định hướng lại luồng Video Pick
Trong `_handle_video_pick`: Sau khi thoát khỏi màn hình xem video hoặc dismiss template về Profile/Feed, hàm xác định màn hình không phải là Camera và chuyển sang tìm/bấm nút create (+) ở đáy màn hình (`_find_bounded_create_button` / `_recover_video_pick_create_entry`) để mở Camera sạch sẽ.

---

## 4. Verification & Testing
- Unit test suite:
  - `test_is_profile_video_playback_surface_matches_playback_ui`: Pass 100%.
  - `test_recover_profile_video_playback_surface_taps_bq7_or_calls_back`: Pass 100%.
  - `test_is_camera_surface_xml_excludes_profile_root`: Pass 100%.
  - `test_is_camera_surface_xml_excludes_feed_root`: Pass 100%.
  - `test_tap_visual_camera_upload_entry_stops_if_camera_lost_after_dismiss_template`: Pass 100%.
- Live verification trên Máy 38: Cơ chế nhận diện và bấm `bq7` đưa màn hình thoát khỏi video playback, cho phép retry tạo entry video an toàn.
