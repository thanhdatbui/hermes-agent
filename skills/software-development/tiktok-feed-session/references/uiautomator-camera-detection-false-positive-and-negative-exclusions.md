# UIAutomator Popup Detection & Negative Exclusions (Incident 28/08/2026)

Use this reference when modifying UIAutomator popup detectors, `benign_popup_registry.py`, or profile verification flows in `tiktok-luot nuoi acc`.

## The Incident
- **Symptom**: 28 machines suddenly entered `status: blocked` after completing 8–11 feed swipes in shift 3 (ca chiều).
- **Root Cause**: `_detect_camera_creation` used naive case-insensitive substring matching (`in xml_content.casefold()`) with generic words (`["10 phút", "60s", "15s", "ẢNH", "VĂN BẢN", "10m", "Photo", "Templates", "CAMERA"]`). On the standard Profile screen, `Ảnh hồ sơ` matched `"ảnh"` and the story/avatar Camera button matched `"camera"`.
- **Failure cascade**: The detector returned `True` -> issued `KEYCODE_BACK` -> TikTok exited Profile back to FYP -> `verify_profile` found no username (`detected: null`) -> classified as `profile account mismatch` -> locked 28 machines with `preserve_blocker_screen`.

## Mandatory Architecture Rules
1. **Negative Exclusions**: Always check if screen has Profile elements (`Đã follow`, `Follower`, `Sửa hồ sơ`, `Menu hồ sơ`, `Chia sẻ hồ sơ`) or FYP Navigation bar (`Trang chủ` + `Hộp thư` + `Hồ sơ`). If present, NEVER classify as Camera overlay.
2. **Compound Matching**: Never match single words like `"ảnh"` or `"camera"`. Require at least 2 shoot durations (`15s`, `60s`, `10 phút`, `10m`, `templates`, `văn bản`) or 1 duration + 1 recording control (`lật`, `hẹn giờ`, `tốc độ`, `bộ lọc`, `thêm âm thanh`).
3. **Fleet XML Regression Gate**: Every detector edit must be validated against all historical `ui.xml` dumps from `D:\Taadaa\runtime\kibe\live\...` to guarantee 0% false positives.
4. **Mandatory Documentation Compliance**: All script/UI handling must comply with `docs/uiautomator.md`.
