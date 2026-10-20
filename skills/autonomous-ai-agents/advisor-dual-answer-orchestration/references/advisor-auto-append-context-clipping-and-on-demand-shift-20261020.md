# Khắc Phục Bẫy Cắt Xén Ngữ Cảnh Tự Động & Chuyển Đổi Sang On-Demand Cho Advisor Sol (20/10/2026)

## 1. Hiện Tượng & Phản Ánh Của Operator
- **Triệu chứng:** Khi Operator trao đổi kỹ thuật hoặc hỏi Coordinator trong session, khối `--- Advisor (Sol / review) ---` tự động chèn vào cuối tin nhắn (auto-append) với nội dung lạc quẻ, bắt bẻ, hoặc yêu cầu cộc cằn:
  > *"Nhưng tao nói thẳng một điểm: tao không thể tự nhận đã thống nhất với Claude nếu trong cuộc trò chuyện này chưa có nội dung trao đổi đó. Mày gửi cho tao đoạn hội thoại hoặc bản thống nhất giữa mày, Claude và hệ thống hiện tại, tao sẽ đọc và chốt một câu dứt khoát..."*
- **Tâm lý Operator:** Cảm thấy Advisor như "ngáo ngơ", thiếu ngữ cảnh, gây đứt gãy mạch đàm đạo và phải giải thích lại từ đầu.

---

## 2. Phân Tích Kỹ Thuật Gốc Rễ (Vì sao đã thiết kế `advisor_context.py` ngày 15/10 mà vẫn bị?)

Dù hệ thống đã bổ sung `agent/advisor_context.py` để trích xuất 3–5 turn gần nhất và gom `field_context`, nhưng thực tế vẫn gãy do 3 nguyên nhân:

1. **Bẫy Cắt Cụt Chuỗi (`_clip_text`) Làm Rách Ngữ Cảnh:**
   - Trong `advisor_context.py`:
     ```python
     MAX_BRIEF_CHARS = 1500
     MAX_TURNS = 5
     MAX_MSG_CHARS = 280
     ```
   - Mỗi tin nhắn bị chém cứng còn 280 ký tự (`head_len=180`, `tail_len=97`, ở giữa biến thành `...`).
   - Nếu ở các turn trước Coordinator có nhắc tới việc *"thống nhất với Claude"*, mẩu hội thoại này bị cắt xén mất sạch ruột kỹ thuật (chỉ còn tiêu đề hoặc câu dẫn dắt cụt lủn). Sol đọc vào thấy nhắc tới "thỏa thuận với Claude" nhưng không thấy nội dung thỏa thuận đâu, dẫn tới phản xạ tự nhiên của một Solution Architect: đòi xem bằng chứng/đoạn chat.

2. **Xung Đột Định Dạng Prompt (JSON thô vs Văn Phong Đối Thoại):**
   - Trong `advisor_tool.py`:
     ```python
     payload = {
         "model": ADVISOR_MODEL,
         "messages": [
             {"role": "system", "content": "You are a read-only planner/advisor. Do not use tools, cause side effects, or approve actions. Return JSON when possible."},
             {"role": "user", "content": json.dumps(env, ensure_ascii=False)}
         ]
     }
     ```
   - Việc bọc toàn bộ bối cảnh vào JSON key-value thô (`{"decision_class": ..., "session_briefing": ...}`) cùng chỉ thị *"Return JSON when possible"* khiến mô hình web pool (`gpt-web-sol`) dễ rơi vào trạng thái đánh giá form/hồ sơ thay vì phản biện tự nhiên theo dòng tư duy giải pháp.

3. **Vòng Lặp Cưa Đôi Payload (`shrink`) Âm Thầm Xóa Dữ Liệu:**
   - Trong `advisor_tool.py`, nếu kích thước payload chạm trần `MAX_PAYLOAD_BYTES (16000)`, hàm `shrink()` sẽ tự động cắt 50% độ dài của trường dài nhất liên tục. Ở các phiên trao đổi dài với nhiều phân tích kỹ thuật, chính `session_briefing` hoặc `current_state` là đối tượng bị cưa gọt đầu tiên, triệt tiêu toàn bộ nỗ lực cung cấp bối cảnh.

---

## 3. Bài Học & Định Hướng Điều Phối (On-Demand Shift)

1. **Ưu Tiên Cơ Chế On-Demand:**
   - Không nên ép buộc Advisor Sol auto-append vào mọi lượt chat có chứa từ khóa đánh giá.
   - Chỉ kích hoạt Sol khi:
     (a) Operator chủ động ra lệnh (`gọi sol`, `hỏi advisor`, `nhờ sol review/plan`).
     (b) Khi Coordinator chạm ngưỡng quyết định kiến trúc lớn (ngã ba đường) cần phản biện độc lập trước khi sửa đổi cấu trúc.
2. **Đóng Gói Bối Cảnh Tập Trung (Dedicated Topical Briefing):**
   - Khi gọi Sol On-Demand, Coordinator phải chủ động soạn 1 gói Briefing nguyên vẹn, không để hàm cắt chuỗi tự động gọt mất phần cốt lõi. Gói này gồm:
     - Bài toán cụ thể đang giải quyết.
     - Đề xuất kiến trúc của Coordinator.
     - Các ràng buộc thực tế hiện trường.
   - Nhờ đó Sol luôn nhận được đề bài trọn vẹn và đưa ra lời khuyên thực chiến, sắc bén.
