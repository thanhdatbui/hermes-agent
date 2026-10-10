# Mobile Telegram Aspect Ratio & Avatar Media Delivery Pitfall (2026-10-10)

## 1. Bối cảnh & Hiện tượng (Operator Frustration)
- **Lệnh của Operator:** *"Nick này của tao đúng k chuẩn hoá lại ava hashtag"* kèm ảnh chụp Profile màn hình điện thoại iPhone (iOS) của nick `@holinh1003`.
- **Hành động của Agent:** Sau khi định danh đúng Máy 226 Tik 2 Admin, sửa workbook, sync kho media 202 và nạp queue SQLite, Agent tự ý viết script Python ghép ảnh composite 3 cột nằm ngang:
  * Kích thước canvas: `1280 x 560` (tỷ lệ dẹt ngang ~2.3:1).
  * Panel 1: Ava cũ cắt từ screenshot.
  * Panel 2: Ava mới vuông 512x512.
  * Panel 3: Giả lập khung tròn viền đỏ TikTok.
- **Phản ứng gay gắt của Operator:** 
  > *"Gửi ảnh lỗi r đm cứ gửi lỗi hoài"*

---

## 2. Nguyên nhân Kỹ thuật Gốc rễ

### A. Cơ chế hiển thị của Telegram Mobile Client
1. **Letterboxing dẹt dí:** 
   - Trên Telegram dành cho di động (iOS/Android màn hình dọc 9:19.5), một ảnh có tỷ lệ dẹt ngang `1280 x 560` sẽ bị client tự động co lại theo chiều ngang màn hình (~380-400pt).
   - Chiều cao hiển thị chỉ còn khoảng `160-180pt`. Toàn bộ khuôn mặt trong từng panel bị thu nhỏ xuống còn dưới 120px, chữ tiêu đề và nhãn chú thích bị nén lại mờ tịt không thể đọc bằng mắt thường.
2. **Cảm giác "Gửi ảnh lỗi / Ảnh hỏng":**
   - Operator nhìn trên điện thoại thấy một dải băng dẹt ngang lọt thỏm giữa khung chat, các chi tiết nhân vật bị teo nhỏ.
   - Operator không yêu cầu xem một bản vẽ đồ họa 3 panel phức tạp; Operator cần nhìn rõ **chân dung avatar mới có đẹp, có đúng nhân vật, có sáng nét không**.
3. **Mất tập trung vào Core Deliverable:**
   - Việc cố gắng "vẽ vời" thêm panel giả lập viền đỏ hay crop dính nền xám khiến ảnh nhìn nhân tạo, dễ dính méo tỷ lệ hoặc viền xước.

---

## 3. Quy chuẩn Bất biến khi Gửi Bằng chứng Avatar trên Telegram

### Quy tắc 1: Luôn ưu tiên gửi trực tiếp file vuông nguyên bản `avatar.jpg` (512x512)
- Khung hình vuông 1:1 (`512x512` hoặc `1080x1080`) là tỷ lệ vàng trên Telegram Mobile:
  * Chiếm trọn chiều rộng khung chat tự nhiên.
  * Không bị letterboxing, không bị ép dẹt.
  * Operator chạm vào là bung full-screen sắc nét từng đường nét khuôn mặt.
- Cú pháp chuẩn:
  ```text
  MEDIA:D:/TIKTOK-videonuoinick/<folder>/avatar.jpg
  ```

### Quy tắc 2: CẤM TUYỆT ĐỐI ghép ảnh composite dạng dẹt ngang (w > h * 1.5)
- Tuyệt đối cấm xếp 3-4 panel dàn hàng ngang tạo thành dải banner dẹt `1280x560` hay `1920x600`.
- Nếu bắt buộc dựng ảnh so sánh đối chiếu (ví dụ So sánh Cũ vs Mới, hoặc 2 Phương án):
  * **Xếp theo chiều dọc (2 tầng):** Tỷ lệ 1:2 hoặc 4:5 (ví dụ canvas `800 x 1000` hoặc `1080 x 1350`). Tầng trên: Cũ, Tầng dưới: Mới.
  * **Lưới vuông 2x2 (nếu có 4 option):** Canvas `1080 x 1080`, mỗi ô `500 x 500`.
  * Kích thước mỗi ô ảnh tối thiểu $\ge 400\text{px}$.

### Quy tắc 3: Hai lớp hình ảnh bắt buộc khi đổi Avatar cho Operator
1. **Lớp 1 (Trước khi up):** Gửi trực tiếp file `avatar.jpg` độc bản (512x512) chuẩn niche để Operator duyệt mắt ngay.
2. **Lớp 2 (Sau khi up lên thiết bị):** Gửi FULL SCREENSHOT Profile (1080x1920) chụp từ thiết bị thật xác nhận đúng username và avatar đã thay đổi.
