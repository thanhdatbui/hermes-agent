# Chuyển Đổi Advisor Sol Sang Cơ Chế On-Demand & Nâng Cấp Streaming SSE (2026-10-20)

## 1. Bối Cảnh & Vấn Đề Gốc Rễ (Root Cause)
- **Hiện tượng:** Operator phản ánh khi trao đổi bình thường trong session, Advisor Sol tự động chèn vào cuối phản hồi với nội dung lạc quẻ, ngáo ngơ:
  > *"Nhưng tao nói thẳng một điểm: tao không thể tự nhận đã thống nhất với Claude nếu trong cuộc trò chuyện này chưa có nội dung trao đổi đó. Mày gửi cho tao đoạn hội thoại hoặc bản thống nhất giữa mày, Claude và hệ thống hiện tại..."*
- **Nguyên nhân kỹ thuật sâu:**
  1. **Auto-append bừa bãi:** Regex `_is_advice_request` bắt mọi từ "nên", "được không", câu hỏi thảo luận thông thường và tự động gọi Advisor Sol sau mỗi turn.
  2. **Rách ngữ cảnh do trần context quá hẹp:** `advisor_context.py` trước đây giới hạn `MAX_MSG_CHARS = 280` (chém giữa thành `...` ở 180 ký tự) và `MAX_BRIEF_CHARS = 1500`. Các thảo luận trước đó về Claude/điều phối bị cắt vụn mất ruột, khiến Sol chỉ thấy cụm từ "thống nhất với Claude" mà không thấy chi tiết kỹ thuật, dẫn đến phản xạ đòi xem chat/log.
  3. **Bẫy non-streaming & timeout 55s trong `advisor_tool.py`:** Request gửi `stream: False` với `DEFAULT_TIMEOUT = 55s`. Khi tăng context, reasoning model ngâm suy nghĩ >40s không có byte keepalive nào làm socket bị timeout.

## 2. Quyết Định Kiến Trúc: Chuyển Sang Hoàn Toàn On-Demand
Operator chốt dứt khoát: **Dừng auto-append sau mọi lượt chat thường. Chuyển 100% sang On-Demand (chỉ gọi khi Operator yêu cầu đích danh hoặc khi cần phản biện plan lớn).**

## 3. Các Thay Đổi Kỹ Thuật Đã Triển Khai (20/10/2026)

### A. Conversation Loop (`D:/Taadaa/Hermes/agent/conversation_loop.py`)
- Định nghĩa danh sách trigger chủ động:
  ```python
  _ADVISOR_EXPLICIT_TRIGGERS = (
      "gọi advisor", "hỏi sol", "gọi sol", "sol thấy sao", "nhờ sol review", "sol lên plan"
  )
  ```
- Hàm `_is_advice_request(message)` chỉ trả về `True` khi tin nhắn chứa một trong các trigger tường minh trên. Các câu hỏi thông thường (tư vấn, có nên, được không...) KHÔNG tự động gọi Advisor.

### B. Mở Rộng Dung Lượng Context (`D:/Taadaa/Hermes/agent/advisor_context.py`)
- Nâng trần độ dài tin nhắn: `MAX_MSG_CHARS = 800` (giữ nguyên vẹn các giải thích kỹ thuật, mã lỗi và đề xuất).
- Nâng trần briefing toàn phiên: `MAX_BRIEF_CHARS = 4000` (đủ cho 5 turns đối thoại chi tiết mà không bị cắt rách).

### C. Nâng Cấp Streaming SSE & Timeout (`D:/Taadaa/Hermes/tools/advisor_tool.py`)
- Chuyển `stream: True` trong payload gửi tới `:20129`.
- Bổ sung hàm đọc streaming `_read_stream_content` bắt SSE `data: ` chunks và `data: [DONE]`.
- Cấu hình timeout đa tầng:
  - `DEFAULT_TIMEOUT = 140`
  - `FIRST_TOKEN_TIMEOUT = 80`
  - `IDLE_TOKEN_TIMEOUT = 20`
- Khớp với OmniRoute `.env`: `STREAM_READINESS_TIMEOUT_MS=80000`, `ACCOUNT_SEMAPHORE_TIMEOUT_MS=90000`.
