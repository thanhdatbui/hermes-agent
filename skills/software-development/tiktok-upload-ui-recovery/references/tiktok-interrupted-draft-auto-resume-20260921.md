# TikTok Interrupted Video Draft Auto-Resume Pattern (2026-09-21)

## Bối cảnh & Hiện tượng
- Khi thiết bị Android farm đang đăng video TikTok mà gặp sự cố mạng, timeout hoặc gián đoạn giữa chừng, TikTok tự động lưu video vào mục **Bản nháp** trên trang Hồ sơ (`ProfileActivity`).
- Đồng thời, TikTok có thể hiển thị banner thông báo thất bại: `"Không thể tải video lên. Đã lưu bản nháp"`.

## Vấn đề cũ
1. **Dọn nháp mù quáng (`_delete_all_profile_drafts`)**: Trước đây ở state `ACCOUNT_READY`, quy trình luôn cố mở thư viện bản nháp để xoá sạch. Điều này khiến video đã render & chuẩn bị sẵn bị mất, hoặc kẹt UI nếu nút xoá không ăn.
2. **Sai lệch Baseline Video Đã Đăng**: Hàm đếm video tile `_profile_video_tile_records` nếu tính cả tile `"Bản nháp: 1"` sẽ làm sai lệch baseline so sánh sau khi đăng.
3. **Mất thời gian đẩy lại media**: Thay vì tận dụng bản nháp đang có sẵn trên thiết bị, quy trình đẩy lại file qua ADB và lặp lại từ đầu.

## Giải pháp chuẩn hóa (TikTok Upload State Machine)

### 1. Giữ bản nháp tại `ACCOUNT_READY`
- Kiểm tra sự hiện diện của text `"bản nháp"` hoặc `"draft"` trên XML Profile.
- Nếu có, set `context.has_profile_draft = True` và KHÔNG gọi xoá bản nháp.

### 2. Tự động Resume tại `VIDEO_PICK`
- Kiểm tra nếu `self.context.has_profile_draft` hoặc XML Profile chứa `"bản nháp"`:
  1. Tap vào tile `"Bản nháp"` trên Profile (`text_contains="Bản nháp"` / `"Draft"`).
  2. Tap vào video draft đầu tiên qua selector (`cover`, `thumbnail`, `video_cover`, `item_root`) hoặc fallback theo bounds `[l, t, r, b]`.
  3. Tại màn hình Editor, tự động tìm và tap nút `"Tiếp"` / `"Next"` / `id/sp3` / `id/next_btn`.
  4. Chờ chuyển cảnh và verify đã vào màn hình Composer (có nút `"Đăng"`, `"Post"` hoặc placeholder `"Thêm mô tả"`).
  5. Return `True` để bypass việc push media mới và chuyển thẳng sang các state tiếp theo (`CAPTION_FILL` / `POST`).

### 3. Loại trừ tile Bản nháp khi đếm video published
- Trong `_profile_video_tile_records`:
  ```python
  tile_texts = " ".join(
      f"{child.attrib.get('text', '')} {child.attrib.get('content-desc', '')}"
      for child in node.iter("node")
  ).casefold()
  if any(k in tile_texts for k in ("bản nháp", "draft")):
      continue
  ```
  Ngăn chặn đếm nhầm tile bản nháp vào baseline video đã xuất bản trên trang cá nhân.
