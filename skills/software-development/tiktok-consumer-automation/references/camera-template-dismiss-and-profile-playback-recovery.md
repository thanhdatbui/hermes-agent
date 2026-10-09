# Phục Hồi Kẹt Màn Hình Xem Video Cá Nhân & Pitfall Camera Dismiss (Case 83)

## 1. Cơ Chế Phát Sinh Lỗi (Root Cause)
- **Lệch màn hình sau khi dismiss template/LIVE:**
  Khi Camera mở ở chế độ LIVE hoặc CapCut Template, flow gọi `_dismiss_capcut_template_surface` (bấm nút back top-left `<` tại `[84, 150]` hoặc `:id/bq3`). Thao tác dismiss này có thể đưa UI thoát hẳn khỏi Camera và rơi về màn hình Hồ sơ (Profile video grid).
- **Tap mù Alternative Thumbnail:**
  Nếu ngay sau khi dismiss template mà hàm không re-dump XML để kiểm tra lại `_is_camera_surface_xml`, flow sẽ tiếp tục tap alternative thumbnail tại tọa độ bên trái `(156, 1574)`. Tại màn hình Profile grid, tọa độ này rơi trúng vào một video tile đã đăng của tài khoản, làm mở màn hình phát video chi tiết (`Profile video playback surface`).
- **Thiếu Recovery Handler cho Playback Surface:**
  Tại trang phát video chi tiết, UI không có nút create `(+)` hay picker media. Nếu `_recover_video_pick_create_entry` không nhận diện được màn hình này, nó sẽ fail-closed với lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## 2. Pitfall Cực Kỳ Nguy Hiểm: `content-desc="camera"` Trong Profile Header
- **Hiện tượng:** Hàm `_is_camera_surface_xml` kiểm tra chuỗi `content-desc="camera"`.
- **Nguyên nhân bug lặp:** Trên nhiều build TikTok 46.x (Samsung SM-G930F/W8), thanh header của Profile chứa shortcut icon để mở Camera nhanh, mang thuộc tính:
  ```xml
  <node resource-id="com.ss.android.ugc.trill:id/d1n" class="android.widget.ImageView" content-desc="Camera" bounds="[661,105][751,195]" ... />
  ```
- **Hậu quả:** Màn hình Profile bị nhận diện sai thành Camera surface (`_is_camera_surface_xml == True`), khiến flow liên tục tap lại `(156, 1574)` -> mở video -> back về profile -> lại tưởng là camera -> tap tiếp.
- **Quy tắc khắc phục:**
  - Bắt buộc kiểm tra loại trừ Profile root hoặc chỉ chấp nhận `camera` khi có kèm các node đặc trưng của chế độ quay (shutter button, `video_record_new_scene_root`, `thêm âm thanh`, v.v.).

## 3. Đặc Trưng Nhận Diện `Profile video playback surface`
- **Nút cài đặt quyền riêng tư:** Resource ID `:id/sl0` / text `"Cài đặt quyền riêng tư"` / `"Privacy settings"`.
- **Lối vào thống kê lượt xem:** Resource ID `:id/view_entrance_text` / text `"lượt xem"` / `"views"`.
- **Nút quay lại profile:** Resource ID `:id/bq7` / `content-desc="Quay lại"` / `content-desc="Back"`.

```python
@classmethod
def _is_profile_video_playback_surface(cls, xml_text: str) -> bool:
    if not xml_text or not isinstance(xml_text, str):
        return False
    if cls._is_verified_media_picker_xml(xml_text):
        return False
    lowered = xml_text.casefold()
    has_privacy_btn = (
        ":id/sl0" in lowered
        or "cài đặt quyền riêng tư" in lowered
        or "privacy settings" in lowered
    )
    has_view_entrance = (
        "view_entrance_text" in lowered
        or "lượt xem" in lowered
        or "views" in lowered
    )
    has_back_btn = (
        ":id/bq7" in lowered
        or 'content-desc="quay lại"' in lowered
        or 'content-desc="back"' in lowered
    )
    return (has_privacy_btn or has_view_entrance) and (has_back_btn or ":id/sl0" in lowered)
```

## 4. Quy Trình Phục Hồi (`_recover_profile_video_playback_surface`)
1. Tìm nút back `:id/bq7` ở vùng header (`top <= 400`), tính tọa độ tâm bounds và thực hiện tap.
2. Nếu không tìm thấy `:id/bq7`, fallback gọi semantic `adapter.back()`.
3. Đợi 1.0 - 1.5s để UI ổn định trở lại Profile / Feed trước khi cho phép create-entry recovery bấm lại nút `(+)`.
4. Luôn tích hợp kiểm tra này trong các vòng lặp chờ Media Picker của `_handle_video_pick` và `_wait_for_verified_media_picker_after_recovery`.
