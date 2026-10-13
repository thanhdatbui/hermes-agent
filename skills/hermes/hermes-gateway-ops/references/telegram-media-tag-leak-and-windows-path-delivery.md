# Telegram Media Tag Leak & Windows Path Delivery Resolution

## 1. Hiện Tượng & Triệu Chứng
- Bot gửi tin nhắn trên Telegram hiển thị nguyên văn dòng chữ text:
  `MEDIA:D:/Taadaa/m67_avatar_new_circle_preview.jpg`
- Người dùng trên điện thoại/desktop chỉ thấy đường dẫn file thô mà không nhận được ảnh nhị phân đính kèm (native photo/document).

## 2. Nguyên Nhân Gốc Rễ Trong Hermes Gateway

### A. Rò Rỉ Thẻ Text Qua Nhánh Transformed (`gateway/run.py`)
- Khi một phản hồi trải qua luồng stream rồi được xử lý qua plugin hooks (như `transform_llm_output`), cờ `_transformed = True` được bật.
- Tại nhánh `edit_message` để chốt tin nhắn cuối cùng, code gọi:
  ```python
  await _sc.adapter.edit_message(
      chat_id=source.chat_id,
      message_id=_sc_msg_id,
      content=response["final_response"],  # LỖI: Gửi final_response thô chứa MEDIA:
      finalize=True,
  )
  ```
- **Hậu quả**: Mặc dù lúc đầu stream, `GatewayStreamConsumer` đã bóc tách ẩn thẻ `MEDIA:`, nhưng lệnh `edit_message` sau cùng lại đè lại toàn bộ `final_response` thô lên tin nhắn, khiến chuỗi text `MEDIA:<path>` lộ chình ình trên màn hình Telegram của người dùng.
- **Khắc phục**:
  Bọc `GatewayStreamConsumer._clean_for_display(response["final_response"])` trước khi truyền vào `content`:
  ```python
  from gateway.stream_consumer import GatewayStreamConsumer
  content = GatewayStreamConsumer._clean_for_display(response["final_response"])
  ```

### B. Hủy File Âm Thầm Trên Windows (`gateway/platforms/base.py`)
- Hàm `validate_media_delivery_path()` kiểm tra đường dẫn an toàn trước khi gửi:
  ```python
  expanded = Path(os.path.expanduser(candidate))
  if not expanded.is_absolute():
      return None
  ```
- **Hạn chế trên Windows**: `PureWindowsPath.is_absolute()` đòi hỏi cực kỳ khắt khe (bắt buộc phải có cả ổ đĩa lẫn dấu gạch chéo gốc như `C:\`). Một số định dạng đường dẫn gốc (POSIX-style hoặc relative drive) khiến `is_absolute()` trả về `False`, khiến tệp đính kèm bị hủy âm thầm (`silently dropped`).
- **Khắc phục**:
  Dùng `os.path.isabs()` thay cho `expanded.is_absolute()`:
  ```python
  expanded = os.path.expanduser(candidate)
  if not os.path.isabs(expanded):
      return None
  expanded = Path(expanded)
  ```

### C. Lệch Môi Trường Runtime (`site-packages` vs Git Repo)
- Các file sửa đổi trong Git repo KHÔNG tự động nạp vào tiến trình Gateway đang chạy nếu tiến trình đó import từ môi trường ảo `site-packages/gateway`.
- **Quy trình chuẩn**:
  1. Vá file trong Git repo.
  2. Copy chính xác các file đã vá sang `site-packages/gateway` của venv đang chạy.
  3. Kiểm tra cú pháp bằng `python -m py_compile`.
  4. Khởi động lại Gateway bằng script detached (`restart_gw_detached.py`) để giải phóng và nạp RAM mới.
