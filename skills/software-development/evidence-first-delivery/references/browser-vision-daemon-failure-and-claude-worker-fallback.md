# Xử Lý Khi Browser Vision Bị Lỗi & Cơ Chế Dự Phòng Bằng Claude Worker CLI

## 1. Vấn Đề Gặp Phải (Browser Vision Failure Mode)
Trong môi trường thực thi automation, công cụ `browser_vision` (dựa trên browser daemon/Playwright/CDP) có thể gặp các lỗi:
- `A daemon for session 'h_...' started concurrently with different daemon configuration`: Xung đột tiến trình nền giữa nhiều phiên làm việc.
- `{"success": false, "error": "Interrupted"}`: Timeout hoặc rớt kết nối pipe giữa agent và browser daemon.
- Snapshot trả về rỗng `(empty page)` khi tải file ảnh local qua giao thức `file:///`.

## 2. Bẫy Nguy Hiểm: Ảo Giác Thị Giác (Visual Hallucination)
- Khi `browser_vision` bị lỗi hoặc không nạp được ảnh, nếu Coordinator cố gắng "đoán mò" nội dung dựa trên tên file hoặc kịch bản mong muốn để trả lời người dùng, kết quả luôn là **ẢO GIÁC HOÀN TOÀN**.
- Ví dụ: Ảnh thực tế là showroom cửa nhựa hoặc người diễn thuyết, nhưng agent khẳng định là "ảnh chân dung chú mèo con mắt xanh to tròn". Điều này vi phạm nghiêm trọng **Invariant Chống Gửi Ảnh Mù / Gửi Đối Phó**.

## 3. Quy Trình Cứu Nguy & Dự Phòng Thị Giác (Vision Fallback Hierarchy)

### Bước 1: Fail-Closed Tức Thì Khi Browser Vision Báo Lỗi
- Nếu `browser_vision` hoặc `browser_navigate` trả về lỗi (Interrupted, Daemon conflict, Empty snapshot):
  * **CẤM TUYỆT ĐỐI** tự viết mô tả hình ảnh hoặc gửi thẻ `MEDIA:` kèm lời khẳng định vô căn cứ.
  * Phải dừng ngay việc sử dụng `browser_vision` cho ảnh đó.

### Bước 2: Kích Hoạt Claude Worker CLI Native Vision (Tầng Dự Phòng 1)
- Trên host Windows có cài đặt `claude_worker.py`, Claude model (Haiku / Sonnet) có khả năng **Multimodal Vision nguyên bản**:
  ```bash
  python D:/Taadaa/tools/claude_worker.py --role worker --max-turns 2 --timeout 30 "Đọc trực tiếp file ảnh <path> bằng mắt thật và mô tả: 1. Có đúng là chủ thể X không? 2. Chi tiết khuôn mặt, biểu cảm, góc nhìn? 3. Có lỗi mép, mờ, hay dính chữ/watermark không?"
  ```
- Claude Worker sẽ đọc trực tiếp từ đường dẫn file trên đĩa cứng, trả về ground truth chính xác 100% về những gì đang hiển thị.

### Bước 3: Đánh Giá Bằng Chứng Thực Tế Trước Khi Gửi
- Chỉ khi nhận được phản hồi xác nhận tích cực từ Claude Worker (hoặc WinRT OCR đối với văn bản UI) mới được phép xuất thẻ `MEDIA:<path>` trong tin nhắn trả lời.
- Nếu kết quả kiểm tra cho thấy ảnh không khớp với yêu cầu: Bắt buộc loại bỏ, trích xuất lại hoặc báo cáo rõ tình trạng thực tế cho người dùng, không bao giờ gửi ảnh sai để đối phó.
