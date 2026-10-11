# Bài học chốt chặn bằng chứng: Xử lý ngoại lệ nhắc lại kết quả trong phiên (2026-10-12)

## 1. Hiện tượng & Vấn đề thực tế
- Khi Coordinator đã hoàn tất công việc ở turn trước, chụp ảnh đầy đủ và gửi thẻ MEDIA hợp lệ được kiểm chứng.
- Ở turn kế tiếp, khi người dùng hỏi thăm hoặc đối thoại tiếp nối ("M làm xong hết r à", "Clgt"), Coordinator trả lời mang tính chất nhắc lại (recap) các kết quả đã làm xong ("Đã đăng xuất nick X, đã đăng nhập nick Y").
- Do câu trả lời nhắc lại có chứa các từ khóa hoàn thành nhưng không đính kèm lại thẻ MEDIA mới, bộ lọc đầu ra tự động gắn cờ vi phạm và chèn thông báo vi phạm bằng chứng vào tin nhắn, gây phiền toái và spam bất tiện cho người dùng.

## 2. Giải pháp cơ học: Session-State Recap Check
- Thay vì quét chuỗi từ vựng mù quáng theo từng lượt độc lập, hook kiểm tra đầu ra cần đối soát trạng thái phiên làm việc (`sess_state`):
  - Tra cứu danh sách các hành động và tài khoản đã được xác minh thành công trước đó trong cùng phiên (`verified_media_details`).
  - Nếu tất cả các hành động được nhắc tới trong câu trả lời đều đã có bằng chứng hình ảnh hợp lệ trong phiên, hệ thống tự động ghi nhận đây là **Recap hợp lệ** và bỏ qua việc gắn cờ vi phạm.
  - Chỉ yêu cầu thẻ MEDIA mới khi có một hành động hoặc đối tượng mới chưa từng được xác minh trước đó trong phiên.

## 3. Quy tắc giao tiếp & Điều phối Farm
- Khi trả lời câu hỏi tiếp nối về tiến độ, Coordinator ưu tiên dẫn chiếu đến bằng chứng đã gửi ở turn trước.
- Khi điều chuyển tài khoản giữa các máy (chuyển nick non sang máy còn trống slot):
  - Tuân thủ quy trình: Bật 2FA -> Ghi nhận vào Excel -> Để sẵn trên Excel chờ ca chạy tự động của máy đó tự nạp.
  - Tuyệt đối không tự ý đăng nhập nhảy cóc sang máy mới trước ca chạy khi chưa có chỉ đạo.
