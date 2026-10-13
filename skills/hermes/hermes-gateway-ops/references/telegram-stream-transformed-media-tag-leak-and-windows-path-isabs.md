# Rò Rỉ Thẻ MEDIA: Trên Telegram Khi Edit Streamed Message & Sửa Đường Dẫn Media Windows

## 1. Hiện Tượng & Triệu Chứng (13/10/2026)
- Bot Telegram Hermes gửi câu trả lời nhưng lộ nguyên văn bản thô:
  ```text
  MEDIA:D:\Taadaa\m67_avatar_new_circle_preview.jpg
  MEDIA:D:\Taadaa\m67_avatar_opt2_circle_preview.jpg
  ```
- Không có ảnh native attachment nào được tải lên chat Telegram, người dùng chỉ thấy đường dẫn text thô vô nghĩa.

## 2. Nguyên Nhân Kỹ Thuật

### A. Lỗi rò rỉ directive trong Stream Consumer (`gateway/run.py` dòng ~20372–20384)
- Khi AIAgent stream câu trả lời tới Telegram, `GatewayStreamConsumer` che giấu các thẻ `MEDIA:<path>` trong các frame stream trung gian.
- Tuy nhiên, sau khi stream xong, nếu có plugin hook biến đổi nội dung (`_transformed` và `_sc is not None` - ví dụ hook chèn thẻ media hoặc format), Gateway gọi `_sc.adapter.edit_message(...)` để chốt tin nhắn cuối.
- Trước đây, nhánh này gửi thẳng `response["final_response"]` thô mà **quên gọi hàm làm sạch `GatewayStreamConsumer._clean_for_display(...)`**.
- Hậu quả: Lệnh edit cuối cùng ghi đè toàn bộ chuỗi text chứa `MEDIA:<path>` lên tin nhắn hiển thị trên Telegram.

### B. Lỗi thẩm định đường dẫn trên Windows (`gateway/platforms/base.py`)
- Hàm `validate_media_delivery_path(path)` trước đây kiểm tra:
  ```python
  if not expanded.is_absolute():
      return None
  ```
- Trên Windows, `PureWindowsPath.is_absolute()` đòi hỏi cả ổ đĩa lẫn gốc (`D:\...`). Với các đường dẫn kiểu POSIX rooted (`/tmp/...`), hàm này trả về `False` và âm thầm hủy bỏ (silently dropped) file đính kèm, khiến adapter không bao giờ gọi `send_photo` hay `send_media_group`.
- Khắc phục: Sử dụng `os.path.isabs(expanded)` thay cho `Path.is_absolute()`.

## 3. Khắc Phục & Kiểm Chứng
1. Tại `gateway/run.py`: Bọc `GatewayStreamConsumer._clean_for_display(response["final_response"])` trước khi gọi `edit_message`.
2. Tại `gateway/platforms/base.py`: Dùng `os.path.isabs(expanded)` để kiểm tra tính tuyệt đối.
3. Restart Gateway detached để nạp bytecode mới vào RAM:
   ```bash
   python D:/Taadaa/tools/restart_gw_detached.py
   ```
