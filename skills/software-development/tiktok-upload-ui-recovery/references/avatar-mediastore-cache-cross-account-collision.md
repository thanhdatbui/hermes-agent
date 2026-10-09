# Bẫy Trùng Avatar Giữa Các Nick Trên Cùng Máy Do Cache MediaStore / Gallery (2026-09-23)

## 1. Hiện tượng & Triệu chứng
- Trên cùng 1 thiết bị nhiều nick (ví dụ Máy 32 có 8 nick), phát hiện 2 nick khác nhau mang **chính xác cùng 1 ảnh đại diện** (MD5 hash trùng nhau 100% trên CDN TikTok), mặc dù trong source gốc (`D:/video goc/<folder>/avatar.jpg`) mỗi nick có 1 file ảnh riêng biệt.
- Trong code `state_machine.py` (`ENSURE_AVATAR`), sau khi upload avatar thành công, hệ thống đã gọi lệnh xóa file:
  ```python
  self.context.media_manager.delete_remote_file(remote_avatar)
  ```
  Nhưng nick sau vẫn bị bốc nhầm ảnh của nick trước!

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lệch pha giữa file hệ thống vật lý và Android MediaStore Database**:
   - Lệnh `delete_remote_file` chỉ chạy lệnh shell `rm` để xóa file ảnh vật lý trên `/sdcard/Pictures/` hoặc `/sdcard/Download/`.
   - Android MediaStore trên Samsung Galaxy S7 (Android 7/8) **KHÔNG tự động cập nhật database tức thì khi file bị xóa bằng lệnh shell rm**.
   - Bản ghi metadata của ảnh cũ vẫn tồn tại trong SQLite database của `com.android.providers.media`, kèm thumbnail cache trong `/sdcard/DCIM/.thumbnails/`.
2. **Cơ chế chọn ảnh của TikTok Photo Picker**:
   - Khi nick tiếp theo vào màn chọn avatar, TikTok query danh sách ảnh từ MediaStore và hiển thị lưới ảnh "Gần đây" (Recent grid).
   - Code FSM chọn ảnh:
     ```python
     image_candidates.sort(key=lambda item: (item["bounds"][1], item["bounds"][0]))
     first = image_candidates[0]
     adapter.tap(*first["center"])
     ```
   - Code luôn luôn tap vào tile ảnh đầu tiên (góc trên bên trái).
   - Nếu ảnh mới push lên chưa được MediaStore index kịp (hoặc MediaStore xếp ảnh cũ còn lưu trong database/thumbnail lên trước), TikTok sẽ hiển thị tile ảnh của nick trước ở vị trí đầu tiên -> Tool tap trúng ảnh cũ!

## 3. Cách khắc phục & Phòng tránh triệt để
1. **Broadcast xóa MediaStore sau khi delete file**:
   - Sau khi `rm` file vật lý, bắt buộc phải phát broadcast quét lại media để Android xóa bản ghi khỏi MediaStore:
     ```bash
     adb shell "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Pictures/<filename>"
     ```
   - Hoặc gọi qua `media_manager.purge_media_rows("av_")` xóa trực tiếp bản ghi trong `content://media/external/images/media`.
2. **Xóa thumbnail cache**:
   - Dọn sạch `/sdcard/DCIM/.thumbnails/` trước khi push ảnh mới.
3. **Scan file mới với timestamp rõ ràng trước khi mở Picker**:
   - Push file mới với tên độc nhất (timestamp).
   - Gọi `am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE` cho file mới và chờ 1-2 giây để MediaStore index xong TRƯỚC KHI mở photo picker của TikTok.
4. **Visual Similarity / Hash Validation**:
   - So sánh ảnh avatar đã chụp trên màn hình Crop (`_capture_avatar_screen`) với source ảnh gốc của nick đó (tính tương đồng `similarity >= threshold`) trước khi nhấn Lưu. Nếu similarity thấp (ảnh lạ / ảnh nick khác), kích hoạt retry hoặc fail-closed thay vì lưu bừa.
