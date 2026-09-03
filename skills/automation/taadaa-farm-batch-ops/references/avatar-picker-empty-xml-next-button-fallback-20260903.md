# Avatar Photo Picker Empty-XML Next Button Fallback (2026-09-03)

## Bối cảnh & Hiện tượng
Trên thiết bị Samsung Galaxy S7 (Android 7), service `uiautomator` có thể bị kill bởi Android LMK hoặc treo tạm thời, khiến `adapter.dump_ui()` trả về chuỗi rỗng (`""` / 0 bytes).

Trong luồng tải Avatar (`ENSURE_AVATAR`):
1. Khi mở picker ảnh (`ProfileAvatarChoosePhotoActivity`), script tap tile ảnh đầu tiên trong album `Pictures`.
2. Sau khi tap ảnh, nút **Tiếp (1)** / **Next (1)** ở góc dưới bên phải chuyển sang màu ĐỎ (`RGB: ~254, 44, 85`, vùng bounds `(824..1032, 1728..1860)`, tâm `(935, 1810)`).
3. Script chuyển sang hàm `_save_avatar_without_story()` để chờ màn hình Cắt ảnh (Crop surface).

## Pitfall đã phát hiện & khắc phục
- **Bug cũ:** Trong `_save_avatar_without_story()`, vòng lặp polling `while time.time() < deadline:` chỉ kiểm tra:
  - Text `"Tiếp (1)"` trong XML (bị miss khi XML rỗng).
  - Visual check `_is_avatar_save_surface_visual` (yêu cầu màu đỏ trải dài cả 2 nửa `552..760` và `824..1032`, trong khi nút Tiếp chỉ nằm ở nửa phải `824..1032`).
  - Khi không có XML và chưa qua màn Cắt, `crop` bị `None` ➔ Hết 25s timeout ném `AVATAR_CROP_OPEN_FAILED` trước khi khối `_is_avatar_next_surface_visual` ở cuối kịp chạy.
- **Khắc phục chuẩn:**
  - Bổ sung kiểm tra `_is_avatar_next_surface_visual(visual_crop)` trực tiếp trong vòng lặp polling của `_save_avatar_without_story()`.
  - Nếu phát hiện màn hình vẫn còn nút Tiếp đỏ ở góc phải, tự động gọi `adapter.tap(*self._scale_avatar_point(adapter, (935, 1810)))` và sleep 2s để chuyển màn hình sang Crop an toàn.
