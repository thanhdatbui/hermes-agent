# Profile Video Playback Trap, Camera False-Positive & Error Unmasking (Case 83 & Case 106, 2026-09-05)

## 1. Sự Cố & Triệu Chứng
- **Mã lỗi:** `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED: Recaptured surface did not prove a labelled bottom-centre create control`
- **Triệu chứng báo ra ngoài:** `upload_subprocess_nonzero` (exit code 1).
- **Hiện trường thiết bị:** Màn hình live dừng tại trang phát video cá nhân (Profile Video Playback Surface), hiển thị nút `:id/sl0` ("Cài đặt quyền riêng tư"), `:id/view_entrance_text` ("lượt xem"), và nút quay lại `:id/bq7`. Không có nút tạo (+) ở đáy màn hình.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Deep Root Cause)

### A. Nhận nhầm Profile Root là Camera Surface (`_is_camera_surface_xml`)
1. Hàm `_is_camera_surface_xml` cũ chỉ kiểm tra chuỗi con:
   - `content-desc="camera"`
   - `text="đăng"` / `text="tạo"` / `text="live"`
2. Trên màn hình Profile root của TikTok:
   - Header có icon camera shortcut (story/capture) mang thuộc tính `content-desc="Camera"`.
   - Tab video đầu tiên của Profile có text `"Đăng"` hoặc `"Đã đăng"`.
   - Bottom navigation bar có tab `"Trang chủ"` và `"Hồ sơ"`.
3. Khi `_is_camera_surface_xml` chạy trên XML Profile root, nó trả về `True` (false-positive nghiêm trọng).

### B. Lạc màn hình sau khi Dismiss Template CapCut / LIVE Mode
1. Khi Camera mở ở chế độ LIVE/Template, hàm `_dismiss_capcut_template_surface` bấm nút thoát top-left.
2. Thao tác dismiss này đưa UI thoát hẳn khỏi Camera và rơi về màn hình Profile.
3. Vì thiếu gate re-dump XML, hoặc vì `_is_camera_surface_xml` nhận nhầm Profile là Camera, hàm `_tap_visual_camera_upload_entry` tiếp tục lấy tọa độ alternative thumbnail `(156, 1574)` để tap.
4. Trên màn hình Profile, tọa độ `(156, 1574)` rơi đúng vào video tile đầu tiên trong grid video cá nhân $\rightarrow$ Mở màn hình phát video chi tiết (Profile Video Playback Surface).

### C. Thiếu Recovery Handler cho Profile Video Playback Surface
1. Khi kẹt ở trang phát video chi tiết, `_recover_video_pick_create_entry` được gọi.
2. Hàm này chỉ xử lý permission dialog, action sheet, CapCut template, media picker và camera surface.
3. Không có nhánh nhận diện trang phát video chi tiết $\rightarrow$ `_find_bounded_create_button` tìm nút (+) thất bại và ném lỗi fail-closed `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

### D. Anti-Pattern: Error Masking thành "upload_subprocess_nonzero"
- Khi tiến trình upload con (`run_post.py`) bị lỗi và thoát với exit code khác 0, batch runner (`run_tiktok_upload_batch.ps1`) hoặc hook cha (`multi_machine_feed_session.py`) trước đây bị hardcode gán chuỗi thô `upload_subprocess_nonzero` mà không đọc `report.json` hay log con.
- Hậu quả: Báo cáo alert trên Telegram ghi nhận thông tin generic vô nghĩa, khiến người vận hành không nắm được lỗi thực tế.

---

## 3. Giải Pháp Kỹ Thuật Chuẩn (Case 83 & Case 106)

### A. Nhận diện và Thoát Màn hình Phát Video Cá Nhân
```python
@classmethod
def _is_profile_video_playback_surface(cls, xml_text: str) -> bool:
    """Nhận diện trang phát video cá nhân (Profile video player)."""
    if not xml_text or not isinstance(xml_text, str):
        return False
    if cls._is_verified_media_picker_xml(xml_text):
        return False
    lowered = xml_text.casefold()
    has_privacy_btn = any(k in lowered for k in (":id/sl0", "/sl0", "cài đặt quyền riêng tư", "privacy settings"))
    has_view_entrance = any(k in lowered for k in ("view_entrance_text", "view_entrance", "lượt xem", "views"))
    has_back_btn = any(k in lowered for k in (":id/bq7", "/bq7", 'content-desc="quay lại"', 'content-desc="back"'))
    return (has_privacy_btn or has_view_entrance) and (has_back_btn or ":id/sl0" in lowered)

@classmethod
def _recover_profile_video_playback_surface(cls, adapter: TikTokAdapter, xml_text: str) -> bool:
    """Tap nút bq7 hoặc gửi phím back để quay về Profile/Feed."""
    if not cls._is_profile_video_playback_surface(xml_text):
        return False
    # Tìm node bq7 ở top <= 400 và tap tâm node; fallback adapter.back()
    ...
```

### B. Loại trừ Tuyệt đối Profile Root và Feed Root khỏi `_is_camera_surface_xml`
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

    # 2. Loại trừ Bottom Navigation Bar (Camera modal ẩn hoàn toàn thanh điều hướng)
    has_home_tab = any(m in folded for m in ('text="trang chủ"', 'content-desc="trang chủ"', 'text="home"', 'content-desc="home"'))
    has_profile_tab = any(m in folded for m in ('text="hồ sơ"', 'content-desc="hồ sơ"', 'text="profile"', 'content-desc="profile"'))
    if has_home_tab and has_profile_tab:
        return False

    # 3. Loại trừ Feed root
    if "long_press_layout" in folded and any(m in folded for m in ("dành cho bạn", "for you", "đang follow", "following")):
        return False

    return any(marker in folded for marker in ("video_record_new_scene_root", ...))
```

### C. Gate Re-dump XML trong `_tap_visual_camera_upload_entry`
- Sau khi gọi `_dismiss_capcut_template_surface`, bắt buộc re-dump UI XML và kiểm tra `_is_camera_surface_xml(current_xml)`.
- Nếu không còn ở camera surface, dừng ngay việc tap alternative thumbnail và trả về `False` để luồng ngoài định hướng lại màn hình.

### D. Bóc Tách Lỗi Chi Tiết (Unmasking `upload_subprocess_nonzero`)
- Luôn ưu tiên đọc `report.json`: trích xuất `reason` và `last_state`.
- Fallback đọc dòng `[ERROR]` hoặc exception cuối cùng từ stderr/stdout.
- Tuyệt đối không để chuỗi thô `upload_subprocess_nonzero` lọt vào Telegram Alert.
