# Telegram Media Delivery Leak and Stream Edit Cleaning

## 1. Triệu Chứng Lỗi
- Thẻ `MEDIA:<path>` xuất hiện lộ liễu dưới dạng văn bản thô trên Telegram thay vì được gửi dưới dạng ảnh/photo đính kèm nguyên bản (`send_photo` / `send_media_group`).
- Người dùng phàn nàn: "Ảnh đâu, sao cứ gửi đường dẫn thô, ai mà xem được trên Telegram".

## 2. Nguyên Nhân Kỹ Thuật (Root Causes)

### A. Rò rỉ thẻ MEDIA qua nhánh `edit_message` sau khi Stream (`gateway/run.py`)
- Khi một turn sử dụng stream consumer (`GatewayStreamConsumer`), các chunk văn bản phát ra đã được làm sạch thẻ `MEDIA:` qua `GatewayStreamConsumer._clean_for_display(text)`.
- Tuy nhiên, khi kết thúc stream, nếu turn có plugin hook can thiệp nội dung (`_transformed` và `_sc is not None`, ví dụ `transform_llm_output`), Gateway thực hiện một cuộc gọi `_sc.adapter.edit_message(...)` để chốt tin nhắn cuối.
- **Lỗ hổng**: Nhánh này từng truyền thẳng `content=response["final_response"]` chưa qua làm sạch. Nếu response mang thẻ `MEDIA:...`, lệnh `edit_message` này sẽ ghi đè văn bản trên Telegram thành toàn bộ chuỗi thô chứa `MEDIA:`, làm lộ thẻ media ra ngoài.
- **Khắc phục**: Luôn bọc `GatewayStreamConsumer._clean_for_display(response["final_response"])` trước khi gọi `_sc.adapter.edit_message(...)`.

### B. Thẩm định đường dẫn trên Windows (`gateway/platforms/base.py`)
- Trong `validate_media_delivery_path()`, việc dùng `Path.is_absolute()` bị lỗi trên môi trường Windows đối với các đường dẫn kiểu POSIX có gốc (ví dụ `/tmp/file.png`) hoặc đường dẫn thiếu định dạng ổ đĩa đầy đủ vì `PureWindowsPath.is_absolute()` yêu cầu cả ổ đĩa lẫn gốc.
- Khi thẩm định trả về `None`, tệp đính kèm bị âm thầm hủy bỏ (silently dropped) và adapter không bao giờ kích hoạt `send_photo`.
- **Khắc phục**: Dùng `os.path.isabs()` để kiểm tra độ tuyệt đối trước khi resolve path trên Windows.

## 3. Khởi Động Lại Gateway Sau Khi Sửa Mã Nguồn
- Vì Gateway chạy ngầm dạng daemon dài hạn (`pythonw.exe`), Python chỉ nạp module một lần vào RAM khi khởi động.
- Sửa code trên đĩa sẽ **không có tác dụng** cho đến khi chạy script khởi động lại tách biệt:
  ```bash
  python D:/Taadaa/tools/restart_gw_detached.py
  ```
- Script này chờ 5 giây để turn hiện tại gửi xong phản hồi, kill các tiến trình gateway cũ và chạy lại qua `Hermes_Gateway.vbs`.
