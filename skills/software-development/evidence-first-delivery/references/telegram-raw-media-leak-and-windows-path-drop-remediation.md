# Telegram Raw Media Leak & Windows Path Drop Remediation (2026-10-13)

**Bối cảnh sự cố:**  
Người dùng nhận tin nhắn trên Telegram bị lộ 2 dòng văn bản thô:
```text
MEDIA:D:\Taadaa\m67_avatar_new_circle_preview.jpg
MEDIA:D:\Taadaa\m67_avatar_opt2_circle_preview.jpg
```
Kèm ảnh chụp màn hình iOS phẫn nộ:
*"Fix luôn vụ gởi ảnh ngu này cái cứ gửi đường dẫn ngu học bố ai xem qua tele đx"*

---

## 1. Phân Tích Kỹ Thuật Hai Điểm Lỗi Cốt Lõi

### 1.1. Lỗi Rò Rỉ Thẻ Media Qua Trình Stream Edit (`gateway/run.py` dòng ~20372–20384)
- **Cơ chế**: Khi Gateway stream tin nhắn tới Telegram (`GatewayStreamConsumer`), bộ lọc `_clean_for_display` bóc tách các thẻ `MEDIA:<path>` để ẩn khỏi giao diện người dùng.
- **Lỗ hổng**: Sau khi stream hoàn tất, nếu có plugin hook biến đổi nội dung (`_transformed` và `_sc is not None`), `GatewayRunner` gọi:
  ```python
  await _sc.adapter.edit_message(
      chat_id=source.chat_id,
      message_id=_sc_msg_id,
      content=response["final_response"], # <-- LỖ HỔNG: Gửi thẳng chuỗi thô chưa lọc
      finalize=True,
  )
  ```
- **Hệ quả**: Do `response["final_response"]` vẫn chứa nguyên văn thẻ `MEDIA:...`, lệnh `edit_message` đè chuỗi thô lên tin nhắn Telegram, làm lộ đường dẫn file ra khung chat của người dùng.
- **Khắc phục chuẩn**: Bắt buộc bọc `GatewayStreamConsumer._clean_for_display(response["final_response"])` trước khi gọi `edit_message`.

### 1.2. Lỗi Thẩm Định Đường Dẫn Tuyệt Đối Trên Windows (`gateway/platforms/base.py`)
- **Cơ chế**: Hàm `validate_media_delivery_path(path)` trước đây kiểm tra:
  ```python
  expanded = Path(os.path.expanduser(candidate))
  if not expanded.is_absolute():
      return None
  ```
- **Lỗ hổng**: Trên Windows, `PureWindowsPath.is_absolute()` đòi hỏi cả ổ đĩa lẫn gốc (ví dụ `C:\`). Một đường dẫn rooted kiểu POSIX (như `MEDIA:/tmp/...` hoặc đường dẫn chuẩn hóa thiếu drive) bị coi là không tuyệt đối.
- **Hệ quả**: File bị âm thầm loại bỏ (`silently dropped`), `_deliver_media_from_response` bỏ qua file, và Telegram hoàn toàn không nhận được lệnh upload tệp ảnh nhị phân.
- **Khắc phục chuẩn**: Đổi sang `os.path.isabs(expanded)` để kiểm tra tính tuyệt đối.

---

## 2. Quy Trình Trích Xuất & Trình Bày Đa Phương Án Avatar Khi User Yêu Cầu Đổi Ảnh

Khi User yêu cầu *"Hình ava khác đi"*:
1. **Trích xuất từ nhiều video HD khác nhau**: Quét các video Full HD 1080p khác trong thư mục gốc của kênh (`4.mp4`, `5.mp4`, `20.mp4`...) để tìm các phân cảnh, góc mặt, ánh sáng và trang phục khác biệt.
2. **Crop chuẩn bố cục hình tròn**: Căn tâm khuôn mặt, bảo đảm khoảng headroom đỉnh đầu ~15-20%, tạo preview vòng tròn viền xanh với nền dim 30%.
3. **Ghép Mosaic đối soát trực quan**: Ghép tất cả các phương án (Cand 1, Cand 2, Cand 3...) vào một bức ảnh mosaic duy nhất kèm nhãn rõ ràng để gửi cho User.
4. **Soi mắt khách quan qua Vision trước khi gửi**: Mở `browser_navigate` và `browser_vision` mô tả trung thực biểu cảm, góc mặt, trang phục của từng option trong báo cáo, không nói suông hay gửi link mù.
