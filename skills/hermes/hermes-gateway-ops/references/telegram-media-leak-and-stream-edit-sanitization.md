# Telegram Media Leak & Stream Edit Sanitization

## 1. Hiện Tượng & Triệu Chứng
- Người dùng nhận tin nhắn trên Telegram bị lộ văn bản thô dạng `MEDIA:D:\Taadaa\path\to\image.jpg`.
- Không thấy ảnh hoặc video được upload đính kèm dưới dạng ảnh/photo tự nhiên của Telegram.
- Người dùng phàn nàn vì bot gửi đường dẫn thô thay vì hiển thị ảnh trên điện thoại.

## 2. Bản Chất Kỹ Thuật & Nguyên Nhân Gốc Rễ

### 2.1. Lỗi Rò Rỉ Thẻ Text Khi Stream Bị Biến Đổi Nội Dung (`gateway/run.py`)
- Khi người dùng nhận tin nhắn qua streaming (`GatewayStreamConsumer`), bộ lọc `_clean_for_display` bóc tách thẻ `MEDIA:` để ẩn khỏi giao diện chat.
- Tuy nhiên, nếu có hook biến đổi kết quả sau khi stream (`_transformed` và `_sc is not None`), hệ thống gọi `edit_message` với `response["final_response"]` thô mà chưa qua lọc `_clean_for_display`.
- Kết quả: Thẻ `MEDIA:` bị đè lại lên màn hình chat dưới dạng văn bản thường.
- **Khắc phục**: Luôn bọc `GatewayStreamConsumer._clean_for_display(response["final_response"])` trước khi thực hiện `edit_message`.

### 2.2. Lỗi Thẩm Định Đường Dẫn Trên Windows (`gateway/platforms/base.py`)
- Trong `validate_media_delivery_path`, việc dùng `Path.is_absolute()` trên Windows yêu cầu khắt khe cả drive lẫn root.
- Một số đường dẫn hợp lệ trên Windows bị đánh giá sai thành không tuyệt đối, dẫn đến việc bị âm thầm loại bỏ (`silently dropped`) và không được chuyển sang bước upload file.
- **Khắc phục**: Dùng `os.path.isabs()` để kiểm tra độ tuyệt đối của đường dẫn trước khi resolve.

### 2.3. Quy Trình Khởi Động Lại Gateway An Toàn
- Do Python lưu bytecode vào RAM, các chỉnh sửa ở mã nguồn gateway cần được nạp lại bằng cách khởi động lại tiến trình:
  1. Trì hoãn 5 giây để tin nhắn trả lời hiện tại hoàn tất gửi tới Telegram.
  2. Quét và dừng các tiến trình gateway cũ bằng `psutil`.
  3. Kích hoạt lại gateway mới qua wrapper `Hermes_Gateway.vbs`.
