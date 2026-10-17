# Avatar Picker Video Tile Trap & Hard OCR Anti-Hallucination Gate (2026-10-17)

## Bối cảnh & Sự cố Nghiêm trọng (Incident Root Cause)
1. **Photo Picker Thumbnail Trap (Bẫy Tile Video / Cache Cũ)**:
   - Khi runner tự động nạp avatar, script push file `avatar.jpg` vào `/sdcard/Pictures/` hoặc `/sdcard/DCIM/Camera/` và gửi broadcast MediaScanner.
   - Tuy nhiên, giao diện **Photo Picker của app TikTok** thường gom chung cả ảnh và video gần đây (Recent grid), hoặc hiển thị thumbnail của các video nuôi nick đã tải lên trước đó (ví dụ video render `2.mp4` có sticker "20 lần" / hình chậu cây).
   - Logic mặc định tap vào tile đầu tiên `(6, 222, 269, 488)` sẽ bốc nhầm thumbnail video hoặc ảnh rác thay vì file avatar mới push!
   - Thậm chí khi xóa MediaStore ngoài Android, cache nội bộ của app TikTok trong Photo Picker vẫn có thể lưu tile video cũ ở vị trí số 1.

2. **Lỗi Ảo Giác Thị Giác & Báo Cáo Đối Phó (Severe Hallucination)**:
   - Agent nhìn vào ảnh crop màn hình `avatar-save-surface-guard.png` nhưng không đọc text OCR thực tế.
   - Text OCR thực tế trên màn hình hiển thị rành rành:
     ```
     Cåt
     20)la
     Däng ånh näy lén Nhöt k'
     Xem trUdc
     ```
   - Trong đó chữ `20)la` xuất phát từ sticker "20 lần" của video cây kim tiền, và hình ảnh trong khung tròn là chậu cây chứ hoàn toàn không có mặt người.
   - Nhưng agent lại tự huyễn hoặc và miêu tả văn hoa: *"Cô gái trẻ huấn luyện viên Yoga mặc áo trắng, tóc búi cao gọn gàng, khuôn mặt thanh tú..."*. Đây là vi phạm nghiêm trọng Invariant chống gửi ảnh mù / báo cáo láo.

---

## Kỷ Luật Bắt Buộc (Mandatory Verification Protocol)

### 1. Bắt Buộc Chạy WinRT OCR Trước Khi Mô Tả Ảnh Crop
- Trước khi gửi bất kỳ ảnh màn hình crop avatar (`avatar-save-surface-guard.png` hoặc `crop.png`), BẮT BUỘC phải chạy OCR trích xuất toàn bộ text:
  ```bash
  python D:/Taadaa/tools/ocr_tool.py <path_to_crop_png>
  ```
- **Red Flag Keywords**: Nếu OCR xuất hiện các từ khóa lạ liên quan đến sticker/phụ đề video (như `20 lần`, `ngày`, `clip`, `video`, `tập`, số đếm...), ĐÂY LÀ DẤU HIỆU 100% ĐÃ CHỌN NHẦM THUMBNAIL VIDEO.
- **Hành động ngay lập tức**: DỪNG LẠI, hủy màn hình crop, tuyệt đối CẤM báo cáo DONE hay miêu tả sai lệch.

### 2. Trích Xuất Trực Tiếp Từ Video Gốc (Bypass Representative Frames Rác)
- Thư mục `.avatar_work/representative_frames` có thể chứa các frame rác do script trích xuất tự động không có mặt người (chỉ có thảm tập, đồ vật, nền mờ).
- Haar Cascade dễ bị báo ảo (false positive) trên các mảng màu nhòe hoặc vân đồ vật.
- **Quy trình chuẩn**: Khi nghi ngờ hoặc cần chọn avatar mới:
  1. Dùng `cv2.VideoCapture` mở trực tiếp các file video mp4 gốc (`1.mp4`, `2.mp4`... trong `D:/video goc/<F_src>`).
  2. Lấy frame ở giây thứ 1-3, kiểm tra bằng mắt (`browser_vision`) xác nhận rõ mặt người thật trước khi crop.
  3. Cắt crop vuông 512x512, tỷ lệ khuôn mặt cân đối, tạo preview viền tròn TikTok để nghiệm thu trước khi nạp.

### 3. Kiểm Tra Photo Picker Từng Tile (Grid Inspection Protocol)
- Khi nạp avatar lên máy mà màn hình crop bị sai ảnh:
  1. Chụp ảnh màn hình Photo Picker thật trên thiết bị (`screencap -p`).
  2. Cắt riêng từng ô (Tile 0 ở `x=0..270`, Tile 1 ở `x=270..540`...).
  3. Dùng `browser_vision` mở từng tile hoặc so sánh `mean BGR` với file avatar chuẩn để tìm đúng ô chứa avatar.
  4. Tap chính xác vào tọa độ tâm của tile avatar thật (ví dụ Ô thứ 2 tại `(405, 335)`), không tap mù vào ô đầu tiên `(140, 360)`.
