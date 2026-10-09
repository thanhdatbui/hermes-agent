# Chẩn đoán lỗi VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED do CapCut Template Dismiss về Profile (2026-09-06)

## 1. Hiện trường & Bằng chứng (Máy 27)
- **Thiết bị**: Máy 27 | Serial: `ce031823912ae0d20c` | Account: `hoangvy5328`
- **Run ID**: `D:/CodexRuntime/tiktok-video/runs/run_ce031823912ae0d20c_20260906_043033`
- **Mã lỗi**: `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- **Artifacts**: `popup_before.xml` chứa UI Profile của `@hoangvy5328` (nút "Tạo một Nhật ký", follower count, bio, tab Hồ sơ).

## 2. Chuỗi sự kiện & Nguyên nhân gốc rễ (Root Cause)
1. **Camera mở và kích hoạt CapCut creation template**:
   - `VIDEO_PICK` tap nút "+" bottom nav.
   - TikTok mở Camera, đồng thời render giao diện CapCut Template / creation hub.
   - `_is_capcut_template_surface` phát hiện và gọi `_dismiss_capcut_template_surface`.
2. **Dismiss template văng về Profile root**:
   - `_dismiss_capcut_template_surface` tap nút đóng/back góc trên trái `(84, 150)` (`bq3`).
   - Trên build và account này, việc đóng template thoát luôn khỏi camera và rơi về màn hình **Hồ sơ cá nhân (Profile root)** thay vì giữ lại camera surface.
   - Khi đó:
     ```python
     if not self._is_camera_surface_xml(current_xml):
         logger.warning("[CAMERA] Sau khi dismiss template màn hình không còn là camera surface; dừng tap alternative thumbnail để luồng ngoài định hướng lại")
         return False
     ```
   - `_tap_visual_camera_upload_entry` trả về `False`.
3. **Vòng lặp Create-entry Recovery thất bại**:
   - Vòng ngoài không tìm thấy picker node (`upload_element = None`).
   - Kích hoạt `_recover_video_pick_create_entry`: từ Profile, recaptured XML tìm thấy nút "+" ở bottom nav và tap lại.
   - TikTok lại mở Camera → lại hiện Template → dismiss lại rơi về Profile.
   - Bounded recovery hết lượt, worker chuyển sang `SOFT REBOOT RECOVERY (AUTOMATION-CORE)`.
   - Soft reboot thất bại do timeout proxy readiness (`proxy readiness timed out for ce031823912ae0d20c`).
   - Kết quả: fail-closed với mã lỗi `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.

## 3. Chữ ký Recovery trong `run_post.py`
- Hàm `_load_video_pick_recovery_binding`:
  - Tại dòng 788: kiểm tra checkpoint có chữ ký `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
  - Nhưng tại dòng 873 và 884: lại ràng buộc cứng `candidate_signature == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"` và `recapture_signature == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"`.
  - Cần đồng bộ chữ ký cho phép retry đối với `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` khi có chỉ định Sol-authorized handoff.

## 4. Hướng xử lý khuyến nghị
- Khi `_dismiss_capcut_template_surface` đưa màn hình về Profile root:
  - Cần nhận diện Profile root (`_is_profile_root` hoặc markers "Sửa hồ sơ", tab "Hồ sơ" active).
  - Điều hướng bấm tab "Trang chủ" (Home/Feed) trước khi tìm create control, hoặc xử lý chuyển tiếp thích hợp thay vì dừng tap và để recovery rơi vào vòng lặp camera-template-profile.
