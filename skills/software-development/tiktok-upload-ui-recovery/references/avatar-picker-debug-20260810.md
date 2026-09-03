# Avatar picker debug — máy 36/38, 2026-08-10

## Triệu chứng chuỗi lỗi avatar (3 signature khác nhau = 3 UI state)

1. `AVATAR_UPLOAD_MENU_MISSING` — không tìm thấy "Tải ảnh lên"/"Thư viện"/g9u trong dropdown.
2. `AVATAR_PICKER_NO_MATCH` best≈0.465–0.466 < threshold 0.600 — không tile nào khớp source.
3. `AVATAR_EDIT_OPEN_FAILED` — màn "Sửa hồ sơ" không mở qua cả 3 nhánh (bút chì UI cũ, UI mới, deep-link).

## Gốc rễ thật (không phải UI build mới)

**uiautomator dump chết** (test `adb shell uiautomator dump` bị `Killed`, `non_xml_ui_dump`,
`uiautomator_idle_state_error`) — cùng bệnh phủ toàn farm. Vì dump chết:

- XML picker không có node → mọi label album (Download/Hình ảnh/Thư viện) "không hiện"
- → rơi vào visual scan → chỉ quét tile ĐẦU TIÊN = video vừa đăng → corr ~0.465 < 0.6 → FINAL_BLOCKED
  (đúng quy tắc không tap mù, nhưng vì lý do sai)

## Quy trình chẩn đoán đúng

1. Xác nhận ảnh đã vào máy: `adb shell ls /sdcard/Download/ | grep avatar` — log
   "Push thành công: /sdcard/Download/avatar_<folder>.jpg" không đủ; kiểm tra mtime kích thước khớp source.
2. Test dump sống/chết: `adb shell uiautomator dump` — Killed/empty = dump chết.
3. Dump chết → chạy B1 ATX-kill recovery TRƯỚC khi kết luận UI.
4. Dump sống → mới tin signature avatar thật.

## Fix handler đã commit (ccd28f3)

- Khi "Download"/"Tải xuống" vắng mặt → thử album ảnh: `Hình ảnh` / `Images` / `Ảnh` / `Camera`.
- Recent-video-grid fallback chỉ khi KHÔNG có album nào; ưu tiên tile IMAGE (không tap tile video đầu mù).
- Coordinate fallback chỉ khi evidence ảnh tĩnh (ảnh picker không phải video-feed); không tap mù.
- Threshold 0.600 / max 4 attempts / FINAL_BLOCKED giữ nguyên.

## Lưu ý vận hành

- PC sleep giết mọi background worker (exit 2, lock handoff PID dead) — archive lock + retry,
  không coi là lỗi máy.
- Chạy avatar 1 máy: worker trực tiếp + `--force-avatar-upload --force-avatar-machines N`,
  KHÔNG qua batch launcher (nó chạy cả farm).
