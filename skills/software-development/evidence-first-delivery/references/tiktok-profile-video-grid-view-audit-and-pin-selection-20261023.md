# TikTok Profile Video Grid View Audit & Zero-Text Avatar Gate (2026-10-23)

## Bối cảnh sự cố & Lời nhắc từ User
- **Sự cố:** Khi chuẩn hóa profile kênh TikTok (chuẩn bị ghim video top view và chọn avatar), Coordinator nhìn lướt màn hình và đọc text OCR phân mảnh từ dưới lên, thấy số `402` và `1.075` view nên vội kết luận: *"Chỉ 1 kênh có video >1000 view, kênh kia toàn ~400 view"*.
- **User chấn chỉnh thẳng thắn:** *"Cả 2 kênh đều có video vài nghìn view mà mày dám bảo chỉ 1 kênh có hơn 1000 view"* và *"Có video 8853 view kìa"*.
- **Hiện trường thực tế khi soi kỹ lại:**
  - Kênh 1 (`@tanglam024`): Có video `2.796` và `3.275` view ngay hàng đầu (Top Row 1).
  - Kênh 2 (`@khoango5771`): Có video `8.853` view (gần 9 nghìn view, Top 1 toàn kênh), `1.111` view, `1.075` view.
  - Về Avatar: Lệnh yêu cầu *"Tự chọn ava. Bỏ cái ava cuối cùng dính đống chữ ra"* đòi hỏi trích xuất khung hình từ video gốc sạch 100% text/watermark.

---

## 1. Nguyên nhân gốc rễ (Root Causes)

1. **Bẫy OCR Phân Mảnh & Điểm Mù Hàng Đầu (Top-Row Blindness):**
   - Trên giao diện TikTok mobile profile, icon play `▷` và số lượt xem nằm ở góc dưới-trái của từng ô thumbnail video.
   - Khi chạy OCR toàn trang (full-screen WinRT OCR), các khối text lớn (Tên hiển thị, username, bio, nút bấm) chiếm ưu thế. Các số view nhỏ ở thumbnail video (như `8.853`, `2.796`, `3.275`) dễ bị gộp nhầm vào subtitle, caption video, hoặc trôi xuống thứ tự đọc sau.
   - Agent đọc lướt các dòng text trả về từ trên xuống, thấy một số view ở hàng 2 hoặc hàng 3 (như `1.075`) thì vội kết luận là video cao nhất, bỏ qua toàn bộ hàng đầu tiên (Row 1) - nơi tập trung video mới nhất hoặc video view khủng nhất.

2. **Bẫy Avatar Trích Xuất Dính Subtitle/Watermark:**
   - Khi trích xuất frame từ video gốc (`D:/video goc/<folder>/<id>.mp4`) bằng script cắt hình theo giây (1s, 2s, 3s), các video thường có subtitle giới thiệu, logo chữ, hoặc caption mở đầu.
   - Nếu trích xuất mù mà không có khâu OCR hậu kiểm, avatar crop vuông sẽ dính chữ rác, phụ đề gây mất thẩm mỹ và không đúng yêu cầu của User.

---

## 2. Quy trình Audit Lưới Video Profile (Video Grid View Audit Protocol)

Mọi tác vụ rà soát view, chọn video ghim (`pin_top_videos.py`) hoặc đánh giá chất lượng kênh BẮT BUỘC tuân thủ:

1. **Lập Ma Trận Tọa Độ Video Grid:**
   - Không được đọc lướt text OCR toàn màn hình.
   - BẮT BUỘC duyệt theo lưới 3 cột x N hàng (tối thiểu 2–3 hàng đầu tiên = 6–9 video).
   - Với mỗi ô `(Hàng R, Cột C)`: Crop riêng vùng thumbnail hoặc trích xuất số view tương ứng.
2. **Kỷ Luật Soi Hàng 1 Trước Tiên (Row 1 First):**
   - Hàng 1 (Row 1) luôn là hàng quan trọng nhất (video mới đăng hoặc video nổi bật).
   - Tuyệt đối CẤM đưa ra kết luận về trần view của kênh trước khi đọc hết 100% số view của Hàng 1.
3. **Chuẩn Hóa Ký Tự Số Lượt Xem:**
   - Dấu chấm phân tách hàng nghìn: `8.853` = 8.853 view (gần 9k view), `1.075` = 1.075 view.
   - Ký tự viết tắt: `K` (* 1.000), `M` (* 1.000.000).
   - Xếp hạng (Rank) giảm dần để chọn đúng danh sách ghim Top 1, Top 2, Top 3.

---

## 3. Quy Trình Trích Xuất Avatar Sạch Không Chữ (Zero-Text Avatar Gate)

Khi tự động chọn avatar từ video gốc theo lệnh chọn avatar sạch / loại bỏ chữ:

1. **Trích xuất đa khung hình:** Cắt các frame vuông `(512, 512)` từ nhiều video gốc trong thư mục (`1.mp4`, `2.mp4`, `3.mp4`...).
2. **WinRT OCR Verification Gate (BẮT BUỘC):**
   - Chạy `python D:/Taadaa/tools/run_winrt_ocr.py <candidate_avatar.jpg>`.
   - Tiêu chí ĐẠT: Số dòng text phát hiện BẮT BUỘC PHẢI BẰNG 0 (`lines == 0`).
   - Nếu phát hiện dù chỉ 1 từ hay ký tự rác (watermark, sub, logo): HỦY NGAY khung hình đó và chuyển sang video khác.
3. **Triển khai & Khóa Cờ:**
   - Lưu avatar đã duyệt vào `video goc/<folder>/avatar.jpg` và `TIKTOK-videonuoinick/<folder>/avatar.jpg`.
   - Cắm ngay 2 cờ bảo vệ:
     - `.manual_avatar_locked`
     - `.manual_hashtag_locked`
