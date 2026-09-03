# Avatar Upload & Edit Profile Layout Compatibility (TikTok Samsung Farm)

## Hiện tượng & Nguyên nhân
1. **Layout Sửa hồ sơ mới (Pencil / Pill Button):**
   - Trên các bản build TikTok mới (như TikTok 46.x trên SM-G930S/F/W8), nút "Sửa hồ sơ" dạng text hoặc ID `edit_profile` không còn xuất hiện trên Profile root.
   - Nút chỉnh sửa được thay bằng icon bút chì (`android.widget.Button` hoặc `ImageView`) nằm cạnh tên/username ở vùng bounds khoảng `[777,510][921,594]` (center `849, 552`).
2. **Kẹt do Profile bị scroll lỡ cỡ sau bước quét grid video baseline:**
   - Trong quá trình kiểm tra baseline grid video, màn hình bị cuộn xuống khiến nút bút chì bị trôi lên trên khỏi viewport.
   - Khi không tìm thấy nút, nếu dùng fallback deep-link `snssdk1233://profile/edit`, TikTok sẽ chặn lại bằng popup modal *"Hoạt động không có sẵn. Để tiếp tục tham gia vào các hoạt động, hãy chuyển sang tài khoản ban đầu..."*, dẫn đến lỗi `AVATAR_EDIT_UNAVAILABLE`.
3. **Màn hình Sửa hồ sơ thiếu title header chuẩn:**
   - Khi mở thành công vào màn Sửa hồ sơ, một số build không có resource ID `p46` hoặc text `Sửa hồ sơ` ở header mà hiển thị trực tiếp item `Thay đổi ảnh` / `Change photo`.

## Giải pháp & Quy tắc xử lý chuẩn
- **Cuộn về đỉnh Profile trước khi tìm Edit button:**
  Thực hiện vuốt `swipe 540 400 540 1500` 1-2 lần để đảm bảo toàn bộ header và nút edit/bút chì hiển thị trên màn hình.
- **Selector nút Edit Profile dạng Icon/Pill:**
  - Nhận diện `android.widget.Button` hoặc `ImageView` có `clickable="true"` trong vùng tọa độ `left: 650..920`, `top: 450..650`.
  - Lọc bỏ các icon tab điều hướng (`desc` chứa "video", "thích", "yêu thích", "khóa", "bài đăng", "thêm người") và các nút tạo nội dung (`text` chứa "tạo", "create", "bản nháp").
- **Nhận diện màn Sửa hồ sơ đã sẵn sàng:**
  `_wait_for_avatar_edit_screen` phải kiểm tra thêm sự xuất hiện của `Thay đổi ảnh` hoặc `Change photo` bên cạnh `p46` và `Sửa hồ sơ`.
- **Cấm lạm dụng deep-link `snssdk1233://profile/edit`:**
  Chỉ dùng khi UI hoàn toàn không mở được và phải xử lý popup "Hoạt động không có sẵn" an toàn (bấm OK / Back) để không làm vỡ phiên.

## 4. Xử lý Avatar Picker & Crop khi mất XML dump (Empty UI Dump)
- **Vấn đề mất XML trên máy Samsung S7 / builds cũ:**
  Khi thiết bị Android bị lag hoặc uiautomator/ATX trả về XML rỗng `""`, các bước dựa vào XML như `"Tiếp (1)" in xml_text` sẽ bị bỏ qua. Nếu màn hình vẫn dừng ở màn chọn ảnh (nút Tiếp màu đỏ góc dưới phải `_is_avatar_next_surface_visual`), vòng lặp polling `_save_avatar_without_story` sẽ chờ hết 25s timeout rồi báo lỗi `AVATAR_CROP_OPEN_FAILED`.
- **Visual Fallback cho nút Tiếp (Next Button):**
  Trong vòng lặp polling của `_save_avatar_without_story`:
  ```python
  visual_crop = self._capture_avatar_screen("avatar-crop-open-visual.png")
  if visual_crop and self._is_avatar_next_surface_visual(visual_crop):
      logger.info("[ENSURE_AVATAR] Selection screen remained (visual); tapping Next button")
      adapter.tap(*self._scale_avatar_point(adapter, (924, 1842)))
      time.sleep(2.0)
      continue
  ```
- **Pitfall: Tránh Partial Match `text_contains="Lưu"`:**
  Chuỗi `"Lưu và đăng"` (màn hình Diary preview / Nhật ký) chứa từ `"Lưu"`. Nếu dùng `text_contains="Lưu"` để tìm nút crop/save sẽ nhận nhầm Diary preview thành màn crop đã sẵn sàng, dẫn tới không thực hiện `adapter.back()` để thoát khỏi Diary preview và gây lỗi `AVATAR_SAVE_SELECTOR_MISSING`. Do đó, kiểm tra `"Lưu"` bắt buộc phải là exact text match.
- **Quy chuẩn `_find_adapter_element`:**
  Ưu tiên gọi `adapter._find_ui_element(xml_text, **kwargs)` để tra cứu trên dump hiện tại. Chỉ gọi `adapter._wait_for_element` nếu adapter không hỗ trợ `_find_ui_element`.
