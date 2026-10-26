# Avatar Picker Tile Bias & Visual-Match Selection Invariant

## 1. Bản Chất Sự Cố: Bẫy Chọn Nhầm Screenshot Cũ (First Tile Bias)

### Hiện Tượng
Trong các ca upload/thay avatar trên TikTok Farm, runner (`run_upload_avatar.ps1` hoặc `state_machine.py`) báo cáo:
`Máy N: THÀNH CÔNG (exit=0, verified=True, status=AVATAR_SMOKE_SUCCESS)`
và workbook cập nhật `Avatar = OK`. Tuy nhiên, khi kiểm tra thực tế trên trang cá nhân thì avatar vẫn là ảnh cũ, không hề thay đổi.

### Căn Nguyên Kỹ Thuật
1. **Thứ tự sắp xếp trong Android Gallery Picker:**
   Khi đẩy file avatar mới (`avatar.jpg`) vào `/sdcard/DCIM/Camera/` hoặc `/sdcard/Pictures/` và gọi MediaScanner, Gallery Picker của TikTok hiển thị danh sách ảnh theo ngày sửa đổi hoặc thứ tự quét.
   Nếu trước đó vừa chụp ảnh màn hình trang cá nhân để kiểm tra hiện trường (`/sdcard/m*_prof.png`), ảnh chụp màn hình này thường nằm ở vị trí đầu tiên (Hàng 1, Cột 1).
2. **Logic chọn mù của runner cũ:**
   Trong `state_machine.py`, hàm `_select_avatar_from_download` sắp xếp các candidate theo tọa độ:
   ```python
   image_candidates.sort(key=lambda item: (item["bounds"][1], item["bounds"][0]))
   first = image_candidates[0]
   adapter.tap(*first["center"])
   ```
   Runner luôn luôn tap cố định vào ô ảnh đầu tiên `image_candidates[0]`.
3. **Vòng lặp tự lừa dối:**
   Ô ảnh đầu tiên chính là ảnh chụp màn hình chứa avatar cũ. Runner chọn ảnh đó, chuyển sang màn hình Cắt (Crop), tap "Lưu", chờ màn hình crop đóng và xác nhận thành công. Kết quả là runner tải lại chính bức ảnh cũ lên tài khoản mà vẫn báo `verified=True`.

---

## 2. Giải Pháp Khắc Phục Cơ Học (Commit `d9cc3db`)

### Nâng Cấp Logic Lựa Chọn Tile Bằng So Khớp Thị Giác
Trong `scripts/tiktok_workflow/state_machine.py`:
Trước khi tap tile ảnh, bắt buộc phải đối chiếu danh sách candidate với file avatar nguồn `expected_path`:

```python
image_candidates.sort(key=lambda item: (item["bounds"][1], item["bounds"][0]))
first = image_candidates[0]
if expected_path and Path(expected_path).is_file():
    try:
        visual_tile = self._avatar_picker_visual_match(Path(expected_path), image_candidates)
        if visual_tile and visual_tile.get("similarity", 0) >= 0.35:
            first = visual_tile
            logger.info(
                "[ENSURE_AVATAR] Visual match tìm thấy tile khớp (sim=%.3f): %s",
                visual_tile.get("similarity", 0),
                first["bounds"],
            )
    except Exception as _vm_err:
        logger.warning("[ENSURE_AVATAR] Visual match lỗi, dùng fallback đầu tiên: %s", _vm_err)

logger.info("[ENSURE_AVATAR] Tap tile ảnh mục tiêu: %s", first["bounds"])
adapter.tap(*first["center"])
time.sleep(1.5)
```

### Nguyên Tắc Vận Hành
1. **Không tin tưởng thứ tự MediaStore / Gallery:** Thứ tự tile trong bộ chọn ảnh của Android không đảm bảo tile đầu tiên là file vừa đẩy qua ADB.
2. **Visual Correlation Gate:** Luôn sử dụng hàm `_avatar_picker_visual_match` với ngưỡng `similarity >= 0.35` để định vị đúng tile tương đồng với file nguồn.
3. **Nghiệm thu hai đầu:** Sau khi bấm Lưu avatar, bắt buộc phải tải lại Profile, chụp ảnh màn hình và đối soát độc lập qua WinRT OCR và kiểm tra vùng avatar trước khi xác nhận hoàn tất.
