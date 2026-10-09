# Machine 22 — profile-photo VIEWER bottom sheet (2026-09-04)

Alert: `unknown TikTok state` kẹt bottom sheet / edit profile trên máy 22.
Live dump trực tiếp lúc điều tra không lấy được (`uiautomator dump` bị Killed,
exit 137; ATX chỉ thấy lockscreen đang sạc) — root cause được chứng minh ở
mức code-level qua fixture offline, canary live sau đó success.

## Hai biến thể sheet (đừng nhầm)

- Picker (đã có detector): `Chụp ảnh / Chọn từ Thư viện / Hủy`.
- Viewer (máy 22, MỚI): `Chụp ảnh / Tải ảnh lên / Xem ảnh`, KHÔNG có nút Hủy.

## Root cause

`detect_profile_photo_chooser`
(`D:\Taadaa\automation-core\src\automation_core\tiktok\benign_popup.py`)
chỉ nhận biến thể picker: bắt buộc gate content-desc `Trang tính dưới cùng`
+ ≥2/3 terms (`chụp ảnh/chọn từ thư viện/hủy`) + bắt buộc tìm được nút Hủy.
Sheet viewer không có `Hủy`, có `tải ảnh lên/xem ảnh` (terms chưa từng tồn tại
trong codebase) → detector trả `None`.
Registry `python_runner/flows/benign_popup_registry.py` không có entry nào cho
photo chooser → sheet viewer đơn lẻ (không kèm title `Sửa hồ sơ`) rơi vào
`unknown TikTok state`, feed kẹt. (`detect_edit_profile_subpage` vẫn match khi
có title, nhưng đó chỉ là nửa hiện trường.)

## Fix (đã apply, canary success)

1. `automation-core/.../tiktok/benign_popup.py`
   - Mở rộng `PROFILE_PHOTO_CHOOSER_TERMS`: thêm `tải ảnh lên/tai anh len/
     upload photo/xem ảnh/xem anh/view photo/view profile photo/huỷ/cancel`
     (+ biến thể `chọn từ thư viên`).
   - Detector chấp nhận cặp photo-menu trong package TikTok kể cả thiếu gate
     sheet; viewer không Cancel → trả match với `close_element=None/back_btn`
     để executor fallback BACK. Không bao giờ tap action ảnh.
   - Mở rộng `EDIT_PROFILE_PHOTO_TERMS` với các term viewer (`chụp ảnh,
     tải ảnh lên, xem ảnh...`).
2. `python_runner/flows/benign_popup_registry.py`
   - Mở rộng fallback text `_detect_edit_profile` với 3 term viewer.
   - Thêm `_detect_profile_photo_chooser` + `_dismiss_profile_photo_chooser`
     (tap Cancel nếu có, else BACK) và đăng ký `profile_photo_chooser_overlay`
     priority 79 (trên `profile_edit_subpage_overlay` 78 để sheet trên cùng
     được xử lý trước).

## Verification recipe (offline, không cần máy live)

- Fixture A (edit + viewer) → chooser + edit match, classify
  `manual-needed:popup`. Fixture B (viewer-only) → chooser match
  (trước fix: `None`/unknown). Fixture C (picker classic) → match.
  Fixture D (feed caption nhắc tới ảnh) → `None`/home, không false-positive.
- Registry: A/B → `profile_photo_chooser_overlay`.
- Pytest: `test_benign_popup_registry.py` 152 passed; `test_classifier.py`
  pass. `test_benign_popup.py` fail 10 case NHƯNG đã verify bằng
  `git stash push` registry file → cây sạch fail y hệt 10 case
  (pre-existing, nhóm facebook/vichanger, không do patch này).

## Canary máy 22 (evidence tại nguồn)

- Lệnh: `run-feed-session.ps1 -Machines 22 -Row 1 -RecoveryTestSwipes 2
  -SkipAccountWorkbookSync -Run` → exit 0, `final_status: success`, 2/2 swipes.
- Artifact: `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\20260904-124940\
  machines\machine_22\20260904-124940` — đọc `summary.txt`/`log.jsonl` trực
  tiếp: safety_summary toàn `ok/known TikTok screen/for-you`, không còn unknown.

## Pitfalls đã gặp

- `D:/Taadaa/tools/inspect_machine.py` hiện chỉ là stub (in `adb devices`).
- Đừng quy kết `unknown state` cho edit-profile khi sheet viewer đứng riêng —
  kiểm tra `photo_chooser in registry` trước (session này: False).
