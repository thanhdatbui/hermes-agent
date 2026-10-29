# Dispatch Receipt Enforcer & Claim-vs-Reality Boundary

## 1. Hiện tượng & Vấn đề gốc rễ
Trong kiến trúc điều phối Agent (Hermes Coordinator):
- **Text & Tool Call sinh đồng thời:** Khi LLM gọi `delegate_task`, đoạn text giải thích ("Em đã dispatch Worker đang chạy ngầm...") được tạo ra liền mạch trước khi tool execution thực sự diễn ra.
- **Guard Reject trông như lỗi mềm:** Nếu Guard chặn (`OUT OF REPO WHITELIST`, `CONTRACT VIOLATION`), LLM bị thiên kiến hoàn thành (Completion Bias), không tự quay xe đính chính mà tiếp tục gửi phản hồi "đang chạy ngầm" ra chat.
- **Hệ quả:** Người dùng bị cung cấp thông tin sai lệch ("báo cáo láo / báo cáo khống") trong khi task chưa hề chạy.

## 2. Kiến trúc giải pháp Receipt Enforcer (Khuyến nghị từ Claude CLI)
Áp dụng cơ chế **Gắn nhãn cơ học (Receipt Enforcer)** tại hook xuất tin nhắn (`gateway/run.py`), KHÔNG thêm LLM verifier, KHÔNG block cứng làm tê liệt luồng chat:

1. **Khớp chính xác tool_call_id:**
   - Quét assistant messages trong turn hiện tại (từ sau `user` message cuối) để lấy toàn bộ `call_id` của tool `delegate_task`.
   - Cấm dùng kết quả từ `terminal` hoặc `read_file` để giả lập JSON receipt.
2. **Xác thực cấu trúc JSON & Status Allowlist:**
   - Tool result của `delegate_task` phải parse được JSON chứa `delegation_id` hoặc `task_id`.
   - `status` phải nằm trong allowlist hợp lệ (`dispatched`, `running`, `started`, `ok`).
   - Nếu có reject marker từ Guard (`OUT OF REPO WHITELIST`, `GUARD`, `CONTRACT VIOLATION`), đánh dấu thất bại và trích xuất lý do.
3. **Gắn nhãn cảnh báo cơ học khi thiếu receipt:**
   - Nếu văn bản phản hồi khớp regex khẳng định (`đã dispatch`, `đang chạy ngầm`, `dispatched worker`), nhưng không có valid receipt:
   - Tự động append banner cảnh báo vào cuối tin nhắn:
     ```text
     ⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]
     Lý do: Lệnh dispatch bị Guard chặn (Contract/Whitelist Violation).
     (Hệ thống cơ học tự động gắn nhãn này do phát hiện lời khẳng định không kèm biên lai hợp lệ).
     ```
4. **Fail-Open & Idempotency:**
   - Toàn bộ hook bọc trong `try/except` có log, không bao giờ làm rơi rụng tin nhắn của người dùng.
   - Kiểm tra tránh gắn banner trùng lặp khi chạy qua nhiều adapter/stream chunks.
