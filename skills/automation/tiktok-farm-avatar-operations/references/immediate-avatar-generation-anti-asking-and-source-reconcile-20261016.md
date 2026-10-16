# Quy Tắc Tự Động Sinh Avatar (Anti-Asking / Cấm Hỏi Xin Phép) & Đối Soát Nguồn Thực Tế (2026-10-16)

## 1. Frustration Signal & Bối Cảnh Thực Tế
- **User Signal:** *"Tạo ava đi chứ hỏi chi v"* (Tạo avatar đi chứ hỏi làm gì nữa).
- **Lỗi vi phạm:** Khi nhận ảnh hồ sơ tài khoản TikTok cần chuẩn hóa ("Chuẩn hoá acc này") và phát hiện tài khoản chưa có avatar (đang mang placeholder camera trắng/đỏ) hoặc avatar bị lệch niche, Coordinator lại đi hỏi:
  *"Bạn có muốn tôi trích xuất ngay 2 phương án Avatar từ video gốc để bạn duyệt rồi nạp lên Máy X không?"*
- **Nguyên nhân gốc rễ:** Vi phạm trực tiếp Invariant người dùng trong Memory và Profile: *"đổi ava tự làm cấm hỏi"*, *"user lệnh là làm ngay cấm hỏi lại"*.

## 2. Quy Tắc Bắt Buộc: Immediate Candidate Generation (Anti-Asking)
Khi User gửi ảnh hồ sơ tài khoản và yêu cầu "Chuẩn hoá acc":
1. **CẤM TUYỆT ĐỐI hỏi xin phép làm:**
   - CẤM hỏi "Có muốn tôi trích xuất avatar không?", "Có muốn tôi chuẩn bị ảnh không?".
   - Mọi câu hỏi xin phép tạo avatar đều bị coi là trốn tránh trách nhiệm và làm chậm tiến độ điều phối.
2. **Quy trình thực thi tức thời (Zero-Delay Pipeline):**
   - **Bước 1:** Đọc ảnh màn hình bằng vision để lấy Username, Display Name, chỉ số, hiện trạng avatar, nội dung 6 video trên lưới.
   - **Bước 2:** Tra cứu tọa độ Farm $O(1)$ qua DB / Excel (`TikX.xlsx`) để xác định Máy, Slot, $F_{vid}$ và $F_{src}$.
   - **Bước 3:** Đối soát chéo video trong $F_{src}$ với video hiển thị trên màn hình TikTok để xác minh đúng nhân vật chủ đạo.
   - **Bước 4 (TỰ ĐỘNG THỰC HIỆN):** Trích xuất ngay 2 phương án Avatar tỉ lệ 1:1 ($512 \times 512$), căn giữa khuôn mặt, chừa khoảng đệm an toàn trên đỉnh đầu (headroom $\ge 10-15\%$) để khi lồng vào vòng tròn TikTok không bị lẹm tóc/sừng/tai/cằm.
   - **Bước 5:** Tạo file ảnh so sánh `comparison_preview.jpg` gồm 2 phương án lồng sẵn viền tròn mask TikTok (bán kính 250px, tâm 256px).
   - **Bước 6:** Soi mắt kiểm định qua Vision, sau đó gửi tin nhắn kèm `MEDIA:<path_to_comparison_preview.jpg>` để User CHỌN Phương án 1 hay Phương án 2.
   *CHỈ ĐƯỢC PHÉP hỏi User chọn PA1 hay PA2; CẤM hỏi có nên tạo hay không.*

## 3. Cạm Bẫy Đối Soát Nguồn $F_{src}$ vs $F_{out}$ vs Stale Avatar
- **Hiện tượng:** Tại tài khoản `@khahoan01` (Máy 61, Slot 4), file `Tik4.xlsx` trỏ $F_{vid}=484$ và $F_{src}=301$.
- Trong thư mục `D:/video goc/484/avatar.jpg` lưu sẵn ảnh 2 con khỉ (ảnh rác/cũ từ niche động vật trước đó), trong khi video thực tế kênh đăng là tiểu phẩm hài kịch sân khấu của nghệ sĩ Hoài Linh, Việt Hương, Ngô Kiến Huy trích từ `D:/video goc/301`.
- **Bài học:** TUYỆT ĐỐI KHÔNG dùng ngay file `avatar.jpg` có sẵn trong folder $F_{vid}$ hay $F_{src}$ nếu chưa kiểm chứng với nội dung video thực tế của kênh. Luôn trích xuất frame từ video tương ứng với các clip có view/nội dung tiêu biểu trên kênh.
