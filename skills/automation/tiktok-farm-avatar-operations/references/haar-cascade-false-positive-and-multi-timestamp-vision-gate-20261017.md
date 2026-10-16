# Bẫy Haar Cascade Bắt Ảo (False Positive) & Quy Chuẩn Thẩm Định Đa Timestamp Qua Vision Gate

## 1. Hiện tượng & Bản chất lỗi (Incident 17/10/2026 - Kênh @inhkhoa0211 / Máy 77)
Khi trích xuất avatar chân dung từ video TikTok bằng Haar Cascade (`haarcascade_frontalface_default.xml`):
- **Bẫy bắt ảo vật thể / họa tiết nền:** Nếu chỉ lấy 1 timestamp cố định (ví dụ `1.mp4` lúc 5s), Haar cascade có thể bắt nhầm họa tiết phông nền (như cánh hoa sen, góc kệ gỗ, bóng đổ) làm khuôn mặt. Kết quả crop ra ảnh nhòe mờ, hoàn toàn không có người.
- **Bẫy góc nghiêng / zoom lệch vành tai:** Ở góc quay nghiêng hoặc khi nhân vật cử động, detector có thể bắt trúng vùng vành tai / thái dương, dẫn đến crop phóng to cận cảnh vào tai, cắt lẹm hoàn toàn trán, mắt, mũi, miệng, cằm.

## 2. Giá trị của Invariant "Soi Mắt Đọc Ảnh Trước Khi Gửi"
- Trong sự cố trên, Coordinator tuân thủ nghiêm ngặt Invariant: Gọi `browser_vision` mở ảnh `opt1_circle.jpg` và `opt2_circle.jpg` ra soi trước khi gửi cho User.
- **Phát hiện ngay lập tức:**
  - Option 1: Không có mặt người, ảnh nhòe mờ đồ vật.
  - Option 2: Zoom cận cảnh vào vành tai, mất 100% ngũ quan.
- **Hành động kịp thời:** Chặn đứng việc gửi ảnh rác cho User và ngăn chặn nguy cơ nạp avatar dị dạng lên tài khoản.

## 3. Quy chuẩn Re-probing Đa Timestamp & Bộ Lọc Kích Thước Khuôn Mặt
Khi trích xuất avatar chân dung từ video, BẮT BUỘC áp dụng quy trình quét đa điểm:
1. **Quét đa video & đa timestamp:** Không thử trên 1 timestamp đơn lẻ. Quét tuần tự các mốc `3s, 5s, 8s, 10s, 12s` trên ít nhất 3 video khác nhau (`1.mp4`, `3.mp4`, `5.mp4`).
2. **Bộ lọc kích thước khuôn mặt (Face Size Gate):**
   - Chỉ chấp nhận các detection có `fw >= 200` và `fh >= 200` (đối với video dọc 1080x1920) để loại bỏ 100% false positive từ hoa văn nền hoặc tai.
3. **Căn tỷ lệ Crop ngũ quan chuẩn (Section 13):**
   - `side = int(fw * 1.5)` (clamp `min(side, w, h)`).
   - `cx = fx + fw // 2`, `cy = fy + int(fh * 0.55)`.
   - `x1 = max(0, cx - side // 2)`, `y1 = max(0, cy - int(side * 0.45))`.
   - Headroom chuẩn: `30 - 50px`.
   - Chin clearance: `> 80px`.
4. **Kiểm tra sạch phụ đề / Banner:**
   - Chạy OCR (`ocr_coords.py`) trên vùng crop. Nếu có chữ hoặc subtitle che mặt -> Bỏ qua timestamp đó và chuyển sang timestamp kế tiếp.
5. **Soi mắt nghiệm thu qua Vision:**
   - Bắt buộc kiểm tra ảnh tròn preview (`_circle.jpg`) qua `browser_vision` để xác nhận: đúng nhân vật trong video grid, đủ ngũ quan, không bị lẹm trán/cằm trước khi xuất trình cho User duyệt.
