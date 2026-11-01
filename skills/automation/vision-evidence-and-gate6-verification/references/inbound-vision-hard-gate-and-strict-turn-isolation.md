# Inbound Vision Hard-Gate & Strict Turn Isolation Architecture

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Tại Sao Agent Bị Mù & Nói Dối Về Ảnh)
- **Thiếu Inbound Gate:** Trước đây hệ thống chỉ có `guard_media_vision_gate.py` ở chiều Outbound (kiểm tra khi phát thẻ `MEDIA:`). Ở chiều Inbound khi User gửi ảnh hoặc chụp màn hình vào, Gateway hoàn toàn không có chốt chặn vật lý nào.
- **Lỗi `agent.aux_accounting` & Mất dấu Multimodal:** Khi User gửi ảnh vào Telegram, Gateway cố gắng gọi auxiliary vision nhưng bị lỗi `No module named 'agent.aux_accounting'`, khiến Gateway không tự phân tích được ảnh và ném ra warning.
- **Hành vi sinh xác suất (Hallucination):** Khi prompt răn đe "Bắt buộc xác nhận đã thấy qua vision", model sinh text theo thói quen tự biên tự diễn, mô tả như thật dù chưa hề gọi tool vision đọc ảnh.
- **Lỗ Hổng Thiếu "Resolution & Quality Gate" ở Outbound:** Gate cũ chỉ bắt mâu thuẫn từ ngữ (contradiction), không đo độ phân giải của crop, dẫn đến việc Agent tự cắt micro-crop 180px rồi phóng to làm vỡ hạt, mờ căm nhưng Gate vẫn cho qua vì "đúng chủ thể cún".

## 2. Giải Pháp Cơ Học Đã Thi Công Tại Gateway (`gateway/run.py` Dòng 11830)
- **Vị trí cưỡng chế:** Nằm ngay sau `agent_result = await self._run_agent(...)` và trước khi gửi bất kỳ ký tự nào ra ngoài chat Telegram/Discord.
- **Strict Turn Isolation:**
  - Lấy `_hist_len = agent_result.get("history_offset", len(history))`.
  - `_turn_msgs = _curr_messages[_hist_len:] if len(_curr_messages) > _hist_len else []`.
  - Tuyệt đối KHÔNG fallback về `_curr_messages` cũ để cấm hoàn toàn việc lấy tool-call của turn trước để qua mặt gate.
- **Kiểm tra Tool Vision Thực Thi Thành Công:**
  - Bắt buộc phải có `tool_calls` hoặc `role == "tool"` mang tên `browser_vision`, `vision_analyze` hoặc `ag_cli_vision`.
  - Bắt buộc nội dung trả về của tool phải có độ dài `> 10` ký tự và không dính lỗi (`error`, `failed`, `traceback`).
- **Fail-Closed 100%:**
  - Nếu phát hiện inbound có ảnh mà chưa có tool vision thành công trong turn hiện tại: Gateway **ghi đè và tịch thu toàn bộ câu trả lời bằng chữ của Agent**, thay thế bằng thông báo chặn cứng:
    `⛔ [GATEWAY BLOCKED - INBOUND VISION GATE]: Tin nhắn có ảnh đính kèm nhưng Agent chưa thực sự gọi tool Vision mở mắt đọc ảnh trong lượt này! Yêu cầu Agent phải gọi tool kiểm tra ảnh trước khi trả lời!`
  - Mọi ngoại lệ trong quá trình kiểm tra đều rơi vào `BLOCK`.

## 3. Quy Trình Vận Hành Bắt Buộc Đối Với Coordinator
1. Khi User gửi ảnh (hoặc phản hồi kèm ảnh): **Bước đầu tiên trong turn BẮT BUỘC PHẢI LÀ GỌI TOOL VISION** (`browser_navigate` + `browser_vision` hoặc `copy_user_img`).
2. CẤM TUYỆT ĐỐI trả lời bằng text chat khi chưa có kết quả từ tool vision.
3. Nếu vi phạm, Gateway sẽ tự động chặn họng và quăng lỗi `GATEWAY BLOCKED`.
4. CẤM crop mẩu nhỏ < 350px rồi upscale lên làm nhòe avatar; dùng tool chuẩn `extract_high_confidence_avatars.py` với Laplacian sharpness >= 90 hoặc dùng kho avatar Studio tuyển chọn sẵn trên Farm.
