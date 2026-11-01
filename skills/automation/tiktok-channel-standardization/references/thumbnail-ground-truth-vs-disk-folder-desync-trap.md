# Bẫy Ám Thị Nhãn Excel / Kho Đĩa vs Mỏ Neo Thumbnail Video Thực Tế

## 1. Ngữ Cảnh & Căn Nguyên Sai Lệch (The Anchoring Hallucination Trap)
- **Hiện tượng:** Khi nhận lệnh chuẩn hoá kênh kèm ảnh profile (`[Image attached at: ...]`), Coordinator tra cứu nhanh ra toạ độ máy và đọc file Excel (ví dụ `Tik5.xlsx` ghi Keyword là `Xe`) hoặc kiểm tra kho đĩa cục bộ `D:/video goc/<F_src>` thấy các clip tin tức giao thông/xe hơi.
- **Hậu quả chết người:** Coordinator bị rơi vào **bẫy neo tâm lý (Anchoring Bias)**. Khi dùng `browser_vision` soi thumbnail video trên ảnh profile, Coordinator bị ám thị và "tự vẽ ra" hình ảnh xe hơi, cabin, cao tốc để khớp với nhãn `Xe` trong Excel, trong khi thực tế mắt thường người dùng nhìn thấy rõ ràng là cảnh **ngồi câu cá bên bờ sông/hồ**!
- Người dùng phát hiện và phản ứng gay gắt: *"Cái video cắn đề xuất là đi câu cá mà? Xe clmm à"*.

## 2. Kỷ luật Mỏ Neo Chân Lý Tuyệt Đối (Ground Truth Precedence)
- **Hierarchy chân lý khi thẩm định ngách:**
  $$\text{Thumbnail/Video Thật Trên Profile} > \text{Video Gốc Trên Đĩa} > \text{Nhãn Keyword Trong Excel/DB}$$
- Video trên màn hình TikTok thực tế là kết quả đã đăng và đang tương tác với thuật toán TikTok. Kho đĩa hoặc file Excel có thể đã bị ghi sai từ lúc khởi tạo đàn nick, hoặc tài khoản đã được đổi luồng đăng video khác mà chưa kịp cập nhật Excel.
- **Quy tắc soi mắt không thiên kiến (Unbiased Vision Protocol):**
  1. Khi nhận ảnh profile, **CẤM tra cứu Excel trước**. Phải crop riêng khu vực lưới video (`full_grid.jpg`) và phóng to 2x-3x.
  2. Dùng `browser_vision` liệt kê trung thực các thực thể vật lý nhìn thấy: mặt nước, bờ cỏ, chiếc thuyền, cần câu, thú cưng, con người, đồ ăn... mà **KHÔNG ĐƯỢC** gán ghép bất kỳ giả định nào về ngách từ trước.
  3. Chỉ sau khi đã xác định chắc chắn thực thể trên thumbnail mới mở Excel để đối chiếu xem có bị **LỆCH NGÁCH (DESYNC)** hay không.

## 3. Quy Trình Xử Lý Khi Phát Hiện Lệch Ngách Thực Tế
- Khi Thumbnail thực tế là **Câu cá / Sông nước** nhưng Excel ghi nhãn `Xe`:
  1. **Thừa nhận ngay lập tức sự thật hiện trường:** Video thực tế đang cắn đề xuất thuộc ngách Câu cá, file Excel đang ghi sai/lệch nhãn.
  2. **Chuẩn hoá toàn diện theo video thực tế:**
     - Tên hiển thị (Nickname): Phù hợp nhân vật & ngách câu cá (ví dụ: `Lan Đi Câu`, `Thanh Lan Fishing`).
     - Tiểu sử (Bio): Năng lượng tích cực, thư giãn sông nước, có dấu 100%.
     - Hashtag: Bộ tag câu cá giải trí `#cauca #dammecauca #caucagiaitri...`.
  3. **Đồng bộ sửa ngược lại Excel:**
     - Sửa cột Keyword trong `Tik<N>.xlsx` thành ngách thực tế (`Câu cá`).
     - Cập nhật Hashtag Pool trong Excel và cắm marker `.manual_hashtag_locked` để tránh các cronjob tự động sau này ghi đè lại nhãn sai cũ.
