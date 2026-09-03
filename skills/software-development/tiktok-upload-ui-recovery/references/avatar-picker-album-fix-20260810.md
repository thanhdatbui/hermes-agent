# Avatar picker: mở album ảnh thật (2026-08-10)

## Bug gốc
Máy 38 fail `AVATAR_PICKER_NO_MATCH` vì picker mở tab "Gần đây" (Recent) là **VIDEO grid** — tile video không bao giờ khớp ảnh avatar (similarity 0.466 < 0.600).

## Fix (commit ccd28f3)
1. Khi tap dropdown album mà "Download"/"Downloads"/"Tải xuống" vắng mặt → thử thêm: **Hình ảnh, Images, Ảnh, Camera** (text + substring).
2. Chỉ khi KHÔNG có album nào mới fallback Recent grid — lúc đó ưu tiên tile **image** (bounds/aspect/media-type hint), và nếu `_remote_avatar_is_newest_media_store_image()` True thì ưu tiên tile mới nhất.
3. Coordinate fallback chỉ khi có evidence ảnh tĩnh (không tap mù trên video grid).
4. Giữ threshold 0.600 / max 4 attempts / FINAL_BLOCKED khi không match.

## Lưu ý vận hành
- Ảnh avatar push vào `/sdcard/Download/avatar_<folder>.jpg` + refresh MediaStore — kiểm tra bằng `adb shell ls -la /sdcard/Download/` trước khi nghi ngờ thiếu ảnh.
- Signature avatar khác nhau là UI state khác nhau:
  - `AVATAR_UPLOAD_MENU_MISSING` → không thấy "Tải ảnh lên"
  - `AVATAR_PICKER_NO_MATCH` → picker mở sai tab
  - `AVATAR_EDIT_OPEN_FAILED` → màn Sửa hồ sơ không mở (3 nhánh: bút chì UI cũ, UI mới, deep-link)
- ForceAvatarMachineList trong batch launcher CHẠY CẢ FARM, không giới hạn máy — muốn chạy 1 máy phải dùng worker riêng: `--machine N --force-avatar-upload --force-avatar-machines N`.