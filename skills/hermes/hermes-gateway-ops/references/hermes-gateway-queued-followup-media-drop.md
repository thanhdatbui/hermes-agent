# Hermes Gateway Queued Follow-Up Media Drop Trap (Lỗi Mất Ảnh Do Hàng Đợi Follow-Up)

Ghi nhận: 20/09/2026.
Phạm vi: Hermes Gateway (`gateway/run.py` & `gateway/platforms/base.py`).

---

## 1. Hiện Tượng
- Khi Coordinator gửi báo cáo kèm ảnh qua tag `MEDIA:<path>`, có tỷ lệ cứ ~7-8 lần gửi thì có 1 lần text tin nhắn đến nơi nhưng ảnh hoàn toàn bị mất.
- User phản ánh: *"Gửi ảnh lỗi r"*, *"Vấn đề hermes gửi ảnh lỗi này là do đâu. T thấy cứ 7-8 lần nhắn là 1 lần bị"*.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Queued Follow-Up Race Condition**:
   - Khi có tác vụ nền (background subagent hoàn tất `[ASYNC DELEGATION BATCH COMPLETE]` hoặc `watch_patterns` notification) đến đúng lúc agent chính vừa hoàn tất lượt suy nghĩ và soạn xong báo cáo cuối.
   - Gateway phát hiện có tin nhắn đang xếp hàng nối tiếp (`Queued follow-up for session ...: final stream delivery not confirmed; sending first response before continuing.`).
2. **Điểm Mù Điều Phối trong `gateway/run.py`**:
   - Tại dòng ~20138 (`gateway/run.py`), để xả tin nhắn đầu tiên trước khi chạy tiếp tin nhắn trong hàng đợi, Gateway chỉ gọi:
     ```python
     await adapter.send(source.chat_id, first_response, metadata=_status_thread_metadata)
     ```
   - Nhánh code này **CHỈ gửi text phản hồi thô** mà **HOÀN TOÀN QUÊN gọi hàm bóc tách và gửi media đính kèm** (`_deliver_media_from_response`).
   - Ngay sau đó, follow-up event kích hoạt lượt chạy tiếp theo đè lên, khiến file media của lượt trước không bao giờ được đưa vào hàng đợi `send_media_group`.

---

## 3. Quy Trình Khắc Phục & Phòng Thủ
1. **Phòng thủ tức thời cho Coordinator**:
   - Không đính kèm tag `MEDIA:` cùng lúc trong lượt tổng kết nếu nhận thấy worker nền sắp kết thúc.
   - Khi user báo mất ảnh, gửi lại ảnh trong một lượt nhắn độc lập không chứa background tasks.
2. **Khắc phục triệt để trong mã nguồn Gateway (`gateway/run.py`)**:
   - Tại block xử lý queued follow-up (sau dòng `await adapter.send(source.chat_id, first_response, ...)`):
     ```python
     if hasattr(self, "_deliver_media_from_response"):
         await self._deliver_media_from_response(first_response, event, adapter)
     ```
   - Đảm bảo toàn bộ media được bóc tách và tải lên nền tảng trước khi chuyển sang event kế tiếp trong queue.
