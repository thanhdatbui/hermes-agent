# TikTok Upload: Xử Lý Màn Hình Bản Nháp (Draft Resume Pipeline)

## 1. Hiện tượng & Vấn đề gốc
- Khi upload video bị đứt quãng (do rớt mạng, kill app, hoặc timeout), TikTok tự động lưu video vào mục **Bản nháp** hiển thị ở tile đầu tiên trên lưới video Profile ("Bản nháp: 1", "36.0 MB").
- Cạm bẫy cũ:
  1. **Xoá nháp mù quáng (`_delete_all_profile_drafts`)**: Tự động tìm nút "Chọn" -> "Chọn tất cả" -> "Xóa". Trên nhiều phiên bản TikTok mới, giao diện quản lý nháp không có nút "Chọn" hoặc xoá thất bại, dẫn tới kẹt flow. Quan trọng hơn, việc xoá nháp làm mất video đã render sẵn cần đăng.
  2. **Đếm nhầm Baseline Video**: Tile "Bản nháp" có clickable node với bounds tương tự video tile. Nếu `_profile_video_tile_records` không lọc bỏ từ khóa "bản nháp" / "draft", số lượng baseline trước khi post bị tính sai (VD tính là 1 video thay vì 0 video). Khi video đăng xong, bản nháp biến mất và video thật xuất hiện -> tổng số tile vẫn là 1 -> `VERIFY_POST` tưởng video chưa đăng và kích hoạt repost sai lầm.

## 2. Giải pháp Chuẩn Hóa (Resume Draft Pipeline)

### Bước 1: Bảo toàn bản nháp tại `ACCOUNT_READY`
- Không gọi `_delete_all_profile_drafts` để xoá.
- Quét XML profile: Nếu có text chứa `"bản nháp"` hoặc `"draft"` -> set cờ `context.has_profile_draft = True` để kích hoạt luồng resume tại `VIDEO_PICK`.

### Bước 2: Loại trừ Bản nháp khỏi Baseline Video Grid
Trong hàm `_profile_video_tile_records(xml_text)`:
```python
tile_texts = " ".join(
    f"{child.attrib.get('text', '')} {child.attrib.get('content-desc', '')}"
    for child in node.iter("node")
).casefold()
if any(k in tile_texts for k in ("bản nháp", "draft")):
    continue
```
Đảm bảo tile Bản nháp không bao giờ được tính vào số video đã public trên Profile.

### Bước 3: Resume Bản nháp trong `_handle_video_pick`
Khi `context.has_profile_draft` là True hoặc màn hình hiện tại có chứa `"bản nháp"`:
Gọi `_resume_draft_from_profile(adapter, xml_text)`:
1. **Tap tile Bản nháp**: `adapter._tap_if_found(xml_text, text_contains="Bản nháp")` hoặc `"Draft"`.
2. **Chọn video bản nháp đầu tiên**:
   - Thử selector resource-id: `cover`, `thumbnail`, `video_cover`, `item_root`.
   - Fallback theo bounds: clickable node có $y \ge 150$, $y \le 1800$, chiều rộng $\ge 150$.
   - Fallback tọa độ an toàn: tap `(180, 360)` trên màn hình 1080x1920.
3. **Chuyển từ Editor sang Composer**:
   - Nếu màn hình là Editor (có nút "Tiếp" / "Next" / resource-id `sp3` / `next_btn`): tap nút "Tiếp".
4. **Xác nhận Composer surface**:
   - Nhận diện `_is_final_composer_surface` hoặc có nút "Đăng" / "Post" / "Thêm mô tả".
   - Ghi nhận telemetry checkpoint:
     `checkpoint["draft_resumed"] = True`
     `checkpoint["draft_resumed_at"] = time.time()`
   - Trả về `True` để hoàn tất `VIDEO_PICK` ngay mà không cần push media mới hay mở gallery.

### Bước 4: Chuyển tiếp State Machine bình thường
- `CAPTION_FILL`: Giữ nguyên hoặc bổ sung hashtag nếu cần.
- `POST`: Tap nút "Đăng" (Post) bình thường.
- `VERIFY_POST`: Đếm số video tăng lên (+1 so với baseline đã loại trừ nháp) -> Verify SUCCESS.
- `UPDATE_WORKBOOK`: Cập nhật trạng thái video đã đăng vào workbook Excel.
