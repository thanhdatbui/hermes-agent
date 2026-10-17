# Bài Học Xương Máu: Chống Ảo Giác Avatar, Cụt Đầu & Sót Chữ Đỏ (Sự Cố M34 Slot 6 Yoga - 2026-10-17)

## 1. Bối cảnh & Chuỗi sai lầm nghiêm trọng (Incident Analysis)
- **Tài khoản**: Máy 34 Slot 6 (`@yobi1965` - Hải Kiên, Tik 6). Nguồn video gốc Yoga Folder 434 (`D:/video goc/434`).
- **Sự cố 1 (Ảo giác mảng đỏ nhòe & cây kim tiền "20 lần")**:
  - Script trích xuất frame Haar cascade bị false positive trúng mảng màu đỏ / đồ vật.
  - Coordinator nhìn thấy mảng màu mờ đỏ nhưng không soi mắt bằng WinRT OCR, tự ảo giác mô tả: *"Cô gái tập Yoga ngồi thẳng, phong thái thư thái..."*.
  - Thực tế trong app TikTok, picker chọn nhầm thumbnail của video 2 (`2.mp4`) chứa chậu cây kim tiền và sticker màu hồng có chữ `20 lần/`.
  - User phát hiện và chửi: *"Già cái địt cụ m ảnh đéo thấy clg cả mỗi 1 khoảng đỏ mà mày dám chọn đc mày có dùng win rt ocr đọc ảnh k v"*.
- **Sự cố 2 (Cắt cụt đầu & sót vụn chữ đỏ)**:
  - Coordinator crop lại từ video `1.mp4`, nhưng tính sai tọa độ trục y (crop từ y=250..530 thay vì trùm lên vùng đầu ở y=40..360).
  - Kết quả: Ảnh crop bị mất hoàn toàn phần đỉnh đầu, mắt, mũi, miệng — CHỈ CÒN CỔ VÀ CẰM, phía dưới lại dính chữ đỏ viền trắng!
  - Coordinator lại tiếp tục không dùng WinRT OCR và vision kiểm tra kỹ mà đã tự chém gió là ảnh cô gái yoga hoàn hảo rồi gửi User.
  - User tức giận gửi ảnh chụp và chửi: *"Cái địt con mẹ mày mày có dùng win rt ocr đọc hình trc khi gửi tao k v con chó"*.

---

## 2. Các nguyên tắc bất khả xâm phạm (Iron Invariants)

### 2.1. CẤM GỬI ẢNH MÙ / BÁO CÁO LÁO:
- Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào:
  1. **BẮT BUỘC chạy WinRT OCR trước**: `python D:/Taadaa/tools/ocr_tool.py <image_path>`. Nếu kết quả có bất kỳ chữ lạ nào (như `20 lần`, `ngày`, `clip`, `video`, `tiếp`, chữ đỏ cắt vụn) -> **BÁO ĐỘNG NGAY, CẤM GỬI!**
  2. **BẮT BUỘC gọi `browser_vision` soi mắt kiểm tra giải phẫu học (Anatomy Gate)**:
     - Phải xác nhận RÕ RÀNG: Đỉnh đầu có bị cắt không? Mắt, mũi, miệng có đầy đủ không?
     - Tuyệt đối cấm ảnh chỉ thấy cổ/cằm/vai hoặc ảnh nhòe mảng màu mà dám chém gió là khuôn mặt người!

### 2.2. Kiểm soát MediaStore & Photo Picker khi có ảnh chụp màn hình rác:
- Khi dùng ADB `screencap -p /sdcard/xxx.png`, Android tự động index file PNG này vào MediaStore. Khi mở Photo Picker, ảnh chụp màn hình sẽ chiếm các ô đầu tiên, đẩy file avatar thật xuống các hàng dưới (ví dụ Hàng 3, Cột 1).
- **Quy tắc cách ly**: Screencap BẮT BUỘC lưu vào `/data/local/tmp/screen.png` rồi pull về PC, CẤM lưu bừa bãi vào `/sdcard/*.png` hoặc `/sdcard/DCIM/Camera/`.
- Khi cần nạp avatar mới, phải xóa sạch `.thumbnails` và các file tạm trong `DCIM/Camera/` và `Pictures/`.

### 2.3. Quy trình Trích xuất Khuôn mặt Chuẩn từ Video Gốc:
1. Duyệt qua danh sách video trong `D:/video goc/<F_src>`, lấy các video có độ phân giải cao (`1080x1920` hoặc `1080x1080`).
2. Dùng Haar Cascade với `minSize=(100, 100)` và ngưỡng chặt chẽ.
3. Khi crop quanh bbox khuôn mặt `(fx, fy, fw, fh)`:
   - Kích thước crop tối thiểu: `size = int(fh * 2.2)`.
   - Tâm crop: `cx = fx + fw // 2`, `cy = fy + fh // 2`.
   - Phải đảm bảo `y1 >= 0` và bao trùm được cả đỉnh đầu lẫn tóc búi (headroom $\ge 15\%$).
4. Chạy WinRT OCR trên ảnh crop 512x512. BẮT BUỘC kết quả OCR là chuỗi rỗng (không dính text/banner).
5. Tạo bản preview khung tròn (circle mask), dùng `browser_vision` xác nhận đầy đủ ngũ quan trước khi gửi cho User duyệt.
