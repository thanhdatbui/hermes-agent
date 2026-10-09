# TikTok Profile Draft Resume & Video Tile Baseline Exclusion (2026-09-20)

## Hiện tượng & Ngữ cảnh
Khi batch upload TikTok gặp sự cố mạng, ứng dụng bị đóng giữa chừng hoặc upload dở chừng, TikTok tự động lưu video vào "Bản nháp" (Draft).
Trên tab Hồ sơ (Profile), vị trí ô video đầu tiên trên lưới (Grid) hiển thị:
- Text: `Bản nháp: 1` (hoặc `Drafts: 1`) kèm dung lượng (ví dụ `36.0 MB`).

## Vấn đề với logic cũ
1. **Dọn nháp mù quáng (`_delete_all_profile_drafts`)**: Code cũ tìm cách bấm vào Bản nháp -> bấm "Chọn" -> "Chọn tất cả" -> "Xóa". Hành động này vừa tốn thời gian, vừa dễ fail do layout TikTok mới đổi nút "Chọn", và quan trọng nhất là xoá mất video đã render/upload dở chừng của người dùng.
2. **Nhiễm bẩn Baseline Video (`_profile_video_tile_records`)**: Nếu tile "Bản nháp" không được loại trừ, nó sẽ bị nhận diện là 1 video tile trong `pre_post_video_count`. Sau khi đăng bản nháp thành công, bản nháp biến thành video thật nhưng tổng số tile trên màn hình không đổi (`pre_post_video_count == post_video_count`), khiến bước `VERIFY_POST` chẩn đoán sai là video chưa lên và đánh fail phiên.

## Giải pháp chuẩn: Draft Resume Workflow

### 1. Tại `ACCOUNT_READY`: Giữ lại bản nháp
- Kiểm tra nếu `xml_text` trên Profile chứa `"bản nháp"` hoặc `"draft"`:
  - Gắn cờ `self.context.has_profile_draft = True`.
  - Không gọi hàm xoá bản nháp (`_delete_all_profile_drafts`).

### 2. Loại trừ tile Bản nháp khỏi Video Grid Scanner (`_profile_video_tile_records`)
- Trong vòng lặp duyệt nodes để tính baseline video đã publish:
  ```python
  tile_texts = " ".join(
      f"{child.attrib.get('text', '')} {child.attrib.get('content-desc', '')}"
      for child in node.iter("node")
  ).casefold()
  if any(k in tile_texts for k in ("bản nháp", "draft")):
      continue
  ```
- Đảm bảo tile Bản nháp không bị tính vào số lượng video public đã có. Khi bản nháp được đăng, video count tăng đúng $+1$.

### 3. Tại `VIDEO_PICK`: Mở bản nháp và điều hướng vào Composer (`_resume_draft_from_profile`)
- Khi `self.context.has_profile_draft` hoặc màn hình có `"bản nháp"`:
  1. **Bấm vào tile Bản nháp**:
     `adapter._tap_if_found(xml_text, text_contains="Bản nháp")` (hoặc `text_contains="Draft"`).
  2. **Bấm vào video bản nháp đầu tiên trong danh sách**:
     - Thử tìm `resource_id="cover"`, `"thumbnail"`, `"video_cover"`, `"item_root"`.
     - Fallback: Tìm clickable node đầu tiên có bounds $y \ge 150$.
     - Fallback tọa độ màn hình 1080x1920: `(180, 360)`.
  3. **Bấm nút Tiếp (Next) nếu ở màn hình Editor**:
     - Quét tìm `text="Tiếp"`, `text="Next"`, `resource_id="sp3"`, `resource_id="next_btn"`.
     - Chuyển sang màn hình Composer (màn hình Đăng).
  4. **Xác nhận vào Composer**:
     - Kiểm tra `_is_final_composer_surface(adapter, current_xml)` hoặc có nút "Đăng" / "Post".
     - Return `True` để hoàn tất `VIDEO_PICK`.

### 4. Các bước tiếp theo
- `CAPTION_FILL`: Giữ nguyên caption đã có của draft hoặc điền thêm nếu trống.
- `POST`: Bấm nút "Đăng" bình thường.
- `VERIFY_POST`: Baseline video tăng $+1$ chính xác.
- `UPDATE_WORKBOOK`: Ghi nhận video đã đăng vào workbook thành công.
