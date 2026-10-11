# Avatar Creator Desync, Badge False-Positive, and Zero-Byte Video Safeguards

## 1. Bẫy False-Positive Face Detection từ Logo / Watermark
- **Hiện tượng:** Các video dạng Infographic / Slide bài giảng (như slide Lịch sử, Giáo dục) thường có logo tròn hoặc huy hiệu ở góc trên (ví dụ huy hiệu Sở GD&ĐT). Các bộ phát hiện khuôn mặt tự động (Haar Cascade / OpenCV) rất dễ nhận diện nhầm vòng tròn huy hiệu có ngọn đuốc/quyển sách thành "khuôn mặt người", tự động crop logo đó lưu thành `avatar.jpg`.
- **Hậu quả:** Kênh TikTok bị gán avatar là logo/phù hiệu trong khi kênh thực tế đăng nội dung hoàn toàn khác.
- **Biện pháp ngăn chặn bắt buộc:**
  1. **Tuyệt đối không tin tưởng mù quáng vào bounding box của face detector:** Phải mở ảnh qua `browser_vision` soi mắt kiểm tra tận nơi xem có đúng mắt, mũi, miệng người thật hay không trước khi lưu/upload.
  2. **Soi mắt lưới video đã đăng trên Profile TikTok:** Khi nhận lệnh đổi avatar từ user ("Đổi ava nick này"), trước khi kết luận chủ đề kênh, bắt buộc phải crop xem lưới video đã đăng trên trang Profile TikTok để xác định đúng phong cách và chủ thể thực tế mà kênh đang đăng tải.

## 2. Lệch Đồng Bộ Giữa Kho Gốc (`video goc`) và Kho Nuôi (`TIKTOK-videonuoinick`)
- **Hiện tượng:** Kho `D:/video goc/<folder>` có thể chứa dữ liệu cũ từ các đợt cào trước đó (stale files), trong khi kho render `D:/TIKTOK-videonuoinick/<folder>` mới là dữ liệu chuẩn đang được runner tải lên TikTok hàng ngày.
- **Quy tắc trích xuất avatar:**
  - Luôn kiểm tra đối chiếu cả hai kho. Nếu có sự lệch pha (mismatch) giữa kho gốc và kho nuôi: **Kho nuôi (`TIKTOK-videonuoinick`) và lịch sử upload thực tế trên TikTok luôn là căn cứ tối cao (Source of Truth)** để trích xuất chân dung creator.
  - Khi phát hiện kho gốc bị lệch/chứa video rác cũ: Phải sao lưu (backup) các video rác cũ ra thư mục lưu trữ riêng, đồng bộ video chuẩn từ kho nuôi sang kho gốc để bảo toàn SSOT hai đầu, và cập nhật lại Keyword / Hashtag Pool trong workbook `Tik<N>.xlsx`.

## 3. Rà Soát File Video Rác 0-Byte (Zero-Byte Placeholder Hazard)
- **Nguyên nhân:** Khi quá trình render dở dang bị ngắt đột ngột (tắt máy, crash script), hệ điều hành có thể tạo sẵn các file `.mp4` rỗng với dung lượng đúng 0 bytes.
- **Hậu quả:** Khi máy chạy đến lượt đăng video đó (`Video Đã Đăng + 1`), script đẩy file 0 bytes lên điện thoại khiến TikTok báo lỗi upload hỏng (`MEDIA_EMPTY`) và máy bị dừng ca fail-closed.
- **Quy trình xử lý chuẩn:**
  1. Quét định kỳ phát hiện các file `.mp4` có kích thước 0 bytes (hoặc < 100KB).
  2. Nếu kho `video goc` có file hợp lệ tương ứng: Copy đè từ kho gốc sang kho nuôi để phục hồi.
  3. Nếu không có file gốc tương ứng: Di chuyển cô lập các file 0 bytes vào thư mục backup riêng để kho nuôi sạch sẽ, đảm bảo runner chỉ lấy các file video hợp lệ.
