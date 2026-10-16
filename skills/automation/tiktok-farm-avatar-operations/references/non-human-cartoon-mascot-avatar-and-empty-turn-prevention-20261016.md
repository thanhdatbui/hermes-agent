# Non-Human Cartoon Mascot & Meme Avatar Extraction & Empty Turn Prevention (16/10/2026)

## 1. Sự Cố & Cạm Bẫy Hiện Trường (Field Hazards)

### 1.1. Bẫy Phản Hồi Rỗng Của Coordinator (Empty Response Trap)
- **Hiện tượng**: Operator phản ánh: *"You just executed tool calls but returned an empty response. Please process the tool results above and continue with the task."*
- **Nguyên nhân**: Khi Coordinator thực hiện xong một chuỗi tool calls (như inspect hiện trường, đọc XML/JSON hoặc kiểm tra file ảnh) nhưng kết thúc lượt trả lời mà không phát sinh text hội thoại, giao diện nhắn tin Telegram/harness nhận về nội dung rỗng (`(empty)`).
- **Quy tắc bắt buộc**: 
  - Mọi lượt sau khi hoàn tất tool call BẮT BUỘC phải xuất ra báo cáo tóm tắt hiện trường bằng chứng (Ground Truth) và kế hoạch hành động cụ thể.
  - Tuyệt đối cấm kết thúc turn chỉ với tool output mà không có lời giải thích hoặc câu hỏi xác nhận cho Operator.

---

### 1.2. Bẫy Haar Cascade Mù Trước Niche Hoạt Hình / Mascot / Phương Tiện
- **Hiện tượng**: Khi kênh thuộc thể loại 2D Animation, Cartoon Meme (như *Học Viện Bò và Gấu*, *Chai tương ớt cúp vàng*), hoặc Xe máy / Phương tiện cơ khí:
  - Script trích xuất tự động dùng `haarcascade_frontalface_default.xml` sẽ trả về `len(faces) == 0`.
  - Một số thuật toán phát hiện biên/vùng tròn dễ bị ảo giác khuôn mặt (*pareidolia*), nhận diện nhầm moay-ơ / trục bánh xe tải thành khuôn mặt (tương tự đầu tàu Thomas).
  - Nguy cơ nghiêm trọng: Script fallback lấy nhầm file `avatar.jpg` rác cũ có sẵn trong kho (vốn là ảnh cắt banner chữ rác *"Bất động sản mắc cạn Lối thoát cho NĐT"* hoặc chữ *"Nghi... Rất Tốt"*).

- **Quy trình xử lý chuẩn (Non-Human & Cartoon Fallback)**:
  1. **Nhận diện kênh phi nhân vật người thật**:
     - Khi kiểm tra lưới 6 video của kênh thấy 100% là nhân vật hoạt hình 2D/3D hoặc xe cộ: **Tắt ngay chế độ dò Haar Cascade người**.
  2. **Trích xuất trực tiếp từ video gốc/render của kênh**:
     - Mở trực tiếp các video tiêu biểu trên lưới (`1.mp4`, `2.mp4`, `4.mp4`) tại giây thứ $1.0s - 2.5s$.
     - Dùng định vị tâm khung hình hoặc lọc ngưỡng màu đối tượng chính (ví dụ da chú Bò, thân chai tương ớt, thân xe máy).
  3. **Crop chân dung linh vật vuông 512x512 có viền kiểm chứng**:
     - Luôn căn tâm đối tượng ở giữa hình tròn ($R=256$, tâm $256, 256$), chừa khoảng thở đỉnh đầu an toàn.
     - Tạo ảnh so sánh ghép đôi (`canvas 580x1050`) giữa 2 linh vật / 2 góc nhìn tiêu biểu để Operator lựa chọn.
  4. **Soi mắt kiểm tra trước khi gửi**:
     - Bắt buộc dùng `browser_navigate` + `browser_vision` mở ảnh canvas so sánh, xác nhận rõ nhân vật không bị cắt mất sừng/tai/cúp trước khi đính kèm thẻ `MEDIA:`.

---

### 1.3. Bẫy Lệnh Python Inline Trên Windows Bash (`open: embedded null character in path`)
- **Hiện tượng**: Khi chạy lệnh terminal `python -c "..."` dạng nhiều dòng hoặc chứa escape nháy phức tạp trên Git-Bash Windows, hook kiểm tra lifecycle có thể gặp lỗi `ValueError: open: embedded null character in path` hoặc kích hoạt guard chặn.
- **Kỷ luật thực thi**:
  - Viết lệnh `python -c` cô đọng trên **đúng 1 dòng đơn** (single-line command), phân tách các lệnh bằng dấu chấm phẩy `;`.
  - Tránh truyền heredoc hoặc newline trong string tham số của `python -c`.
