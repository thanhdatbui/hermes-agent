# Profile Root Camera False-Positive & Profile Video Playback Recovery (2026-09-05)

## 1. Triệu chứng & Bối cảnh lỗi
- **Triệu chứng:** Batch runner báo lỗi `upload_subprocess_nonzero` (exit code 1) trên máy farm Samsung S7/Android 7.
- **Log lỗi trong report.json:** `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`.
- **Hiện trường thực tế:** Màn hình máy bị kẹt tại trang xem chi tiết video cá nhân (Profile video player), có nút "Cài đặt quyền riêng tư", "lượt xem", và nút back `<` ở góc trên cùng bên trái (`:id/bq7`).

## 2. Phân tích nguyên nhân gốc rễ (Deep Root Cause)
1. **Lỗi nhận nhầm Profile root là Camera (`_is_camera_surface_xml` false-positive):**
   - Trong `scripts/tiktok_workflow/state_machine.py`, hàm `_is_camera_surface_xml` kiểm tra các chuỗi con như `content-desc="camera"`, `text="camera"`, `text="đăng"`, `text="tạo"`.
   - Trên TikTok Profile layout mới:
     - Header của Profile có icon shortcut chụp ảnh/story mang `content-desc="Camera"` (bounds `[661, 105][751, 195]`).
     - Tab video đầu tiên của Profile có text `"Đăng"` hoặc `"Bài đăng"`.
   - Do đó, khi UI rơi về Profile (sau khi dismiss CapCut template hoặc back về), `_is_camera_surface_xml` nhận nhầm Profile root là Camera.
2. **Tap mù thumbnail video (`_tap_visual_camera_upload_entry`):**
   - Vì tưởng lầm Profile là Camera, script kích hoạt `_tap_visual_camera_upload_entry`, chụp màn hình Profile và tính toán alternative thumbnail tại góc dưới trái `(156, 1574)`.
   - Tọa độ `(156, 1574)` tap trúng ngay video tile đầu tiên trong grid video của tài khoản trên Profile -> mở trang phát video chi tiết (`Profile video playback surface`).
3. **Kẹt vòng lặp không có nút Create (+):**
   - Trang xem video cá nhân không có nút (+) create control ở đáy màn hình.
   - `_find_bounded_create_button` không tìm thấy nút (+) -> kích hoạt `_recover_video_pick_create_entry`.
   - Vì thiếu nhánh xử lý trang video player, hàm fail-closed ném `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## 3. Giải pháp chuẩn hóa (3 Tầng)

### Tầng 1: Loại trừ triệt để Profile & Feed root khỏi `_is_camera_surface_xml`
```python
@classmethod
def _is_camera_surface_xml(cls, xml_text: str) -> bool:
    if not xml_text or not isinstance(xml_text, str):
        return False
    if cls._is_profile_video_playback_surface(xml_text):
        return False

    folded = unicodedata.normalize("NFC", xml_text).casefold()
    if cls._has_gallery_surface_markers(folded):
        return False

    # 1. Loại trừ Profile root markers
    profile_root_markers = (
        "sửa hồ sơ", "chỉnh sửa hồ sơ", "edit profile", "chia sẻ hồ sơ",
        "thêm tiểu sử", "hoàn tất hồ sơ", "complete profile", "add bio",
        "menu hồ sơ", "profile menu", ":id/ny0", "/ny0",
    )
    if any(marker in folded for marker in profile_root_markers):
        return False

    # 2. Loại trừ Bottom Navigation Bar của Root tabs (Feed/Profile)
    # Camera modal ẩn hoàn toàn thanh điều hướng đáy
    has_home_tab = any(m in folded for m in ('text="trang chủ"', 'content-desc="trang chủ"', 'text="home"', 'content-desc="home"'))
    has_profile_tab = any(m in folded for m in ('text="hồ sơ"', 'content-desc="hồ sơ"', 'text="profile"', 'content-desc="profile"'))
    if has_home_tab and has_profile_tab:
        return False

    # 3. Loại trừ Feed root
    if "long_press_layout" in folded and any(m in folded for m in ("dành cho bạn", "for you", "đang follow", "following")):
        return False

    # 4. Chỉ chấp nhận các markers camera thật sự
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

### Tầng 2: Tự động nhận diện và phục hồi khi kẹt Profile Video Player
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
        or "/sl0" in lowered
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
        or "/bq7" in lowered
        or 'content-desc="quay lại"' in lowered
        or 'content-desc="back"' in lowered
    )
    return (has_privacy_btn or has_view_entrance) and (has_back_btn or ":id/sl0" in lowered)

@classmethod
def _recover_profile_video_playback_surface(cls, adapter, xml_text: str) -> bool:
    if not cls._is_profile_video_playback_surface(xml_text):
        return False
    # Ưu tiên tap nút back top-left :id/bq7 (bounds [18, 72][174, 228])
    # Fallback gọi adapter.back()
    ...
```

### Tầng 3: Gate re-dump XML trong `_tap_visual_camera_upload_entry`
Sau khi dismiss CapCut template hoặc chuyển LIVE mode, bắt buộc re-dump XML và kiểm tra `_is_camera_surface_xml(current_xml)`. Nếu giao diện đã rơi về Profile hoặc Feed, dừng ngay việc tap alternative thumbnail `(156, 1574)` và trả về `False` để luồng ngoài tìm nút (+) mở lại Camera.
