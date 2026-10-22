# Bẫy Nhìn Lướt Lưới Video TikTok Bỏ Sót Video Nghìn View (TikTok Grid View Count Audit Trap)

## 1. Bối cảnh sự cố (23/10/2026)
Khi thực hiện chuẩn hóa hồ sơ và kiểm tra video ghim (Pin Top >= 1.000 view) cho 2 kênh TikTok farm (`@tanglam024` trên Máy 42 và `@khoango5771` trên Máy 43), Agent soi ảnh chụp màn hình Profile của cả 2 máy.
Do đọc lướt nhanh và chỉ chú ý các số view 400-500 ở các hàng dưới hoặc chỉ bắt được 1 số `1.075`, Agent đã đưa ra kết luận sai lệch nghiêm trọng: *"Chỉ 1 kênh có video trên 1.000 view, kênh còn lại chưa đạt mốc này"*.
User lập tức chỉnh đốn gay gắt:
> *"Cả 2 kênh đều có video vài nghìn view mà mày dám bảo chỉ 1 kênh có hơn 1000 view"*

Sau khi crop trực tiếp lưới video và soi mắt từng thumbnail qua thị giác máy tính:
- Kênh 1 (`@tanglam024`): Video 1 (Hàng 1, Cột 1) đạt **`4.081` view**; Video 2 (Hàng 1, Cột 2) đạt **`2.428` view** (Có 2 video vài nghìn view).
- Kênh 2 (`@khoango5771`): Video 1 (Hàng 1, Cột 1) đạt **`1.075` view**; Video 2 (Hàng 1, Cột 2) đạt **`3.003` view**; Video 3 (Hàng 1, Cột 3) đạt **`4.544` view** (Có 3 video trên nghìn view, trong đó có 2 video trên 3k - 4k view).
Agent đã nhìn sót hoàn toàn hàng đầu tiên (Row 1) của lưới video - nơi chứa các video đạt view cao nhất của kênh!

## 2. Nguyên nhân kỹ thuật & Tâm lý
1. **Bẫy Đọc Lướt Bỏ Sót Hàng Đầu (Top-Row Blindspot):** Mắt nhìn hoặc OCR tự động thường bị phân tâm bởi các số to ở phần Header/Bio (Followers, Likes) rồi nhảy xuống vùng giữa/dưới của lưới video. Hàng 1 của lưới video nằm ngay sát tab icon (Video / Khóa / Tim) rất dễ bị bỏ qua nếu không quét theo ma trận.
2. **Định Kiến Số Trung Bình (Median Bias):** Khi thấy hàng loạt video ở Hàng 2 và Hàng 3 đều nằm ở mức 400 - 500 view, Agent vội suy diễn toàn bộ kênh đều lẹt đẹt mà không kiểm tra kỹ từng ô ở Hàng 1.
3. **Thất Thoát Nhãn View Trên OCR Thuần:** Text view hiển thị ở góc dưới bên trái của mỗi thumbnail có font chữ màu trắng với nền mờ. Với các video thumbnail có nền sáng hoặc nhiều chi tiết, OCR toàn màn hình dễ bỏ sót text của các cột 2 và 3.

## 3. Kỷ luật Bắt Buộc: Rà Soát Lưới Video Theo Ma Trận (Matrix Audit Protocol)
Khi kiểm tra lưới video trên Profile TikTok để audit số liệu, đánh giá kênh hoặc chọn video ghim (Pin Top):

1. **CẤM KẾT LUẬN ĐỊNH LƯỢNG MÙ:**
   - Tuyệt đối CẤM kết luận *"Kênh không có video trên 1k"* hoặc *"Chỉ có 1 video view cao"* khi chưa liệt kê cụ thể số liệu từng ô của ít nhất 2 hàng đầu tiên (6 video mới nhất).

2. **QUY TRÌNH QUÉT MA TRẬN 3 CỘT (3xN MATRIX):**
   Bắt buộc đọc và liệt kê số view theo đúng tọa độ từng ô:
   - **Hàng 1:**
     * Ô (1, 1) [Cột trái]: Số view = ?
     * Ô (1, 2) [Cột giữa]: Số view = ?
     * Ô (1, 3) [Cột phải]: Số view = ?
   - **Hàng 2:**
     * Ô (2, 1), Ô (2, 2), Ô (2, 3)...

3. **CẮT CỤM THUMBNAIL (TILE CROP) KHI OCR THIẾU:**
   - Nếu OCR toàn màn hình không bóc tách đủ số cho cả 3 cột, BẮT BUỘC cắt riêng vùng lưới video (`y: 400..1280` tùy độ phân giải màn hình) hoặc dùng công cụ thị giác (`browser_vision` / local LLM vision) soi trực tiếp vào từng ô để đọc số chính xác 100%.

4. **ĐỐI SOÁT CHUẨN GHIM PIN TOP (PIN >= 1.000 VIEW):**
   - Phải xác định đúng Top 1, Top 2, Top 3 view cao nhất thực tế của kênh.
   - Không được ghim nhầm clip thấp view hoặc bỏ sót clip đột biến vài nghìn view chỉ vì lười soi kỹ hàng đầu.
