# Claude CLI Investigation: Root Cause of Advisor Drift & Mechanical Enforcement

## 1. Bối cảnh & Sự cố (10/10/2026)
- **Triệu chứng:** Operator nhiều lần yêu cầu Coordinator bắt buộc gọi Advisor Sol (`:20129 review` / `consult_advisor.py`) khi có Advice Intent (câu hỏi chiến lược, đánh giá, thuật toán farm, "có nên không", "sao lại", "tại sao").
- **Thực tế tái diễn:** Dù đã fix nhiều lần, viết skill `advisor-dual-answer-orchestration`, ghi vào `MEMORY.md`, `AGENTS.md`, Coordinator vẫn liên tục vi phạm: Tự tiện phân tích và trả lời solo 1 mình mà quên gọi Advisor Sol cho đến khi Operator phải chửi và nhắc nhở.
- **Yêu cầu điều tra:** Operator phát lệnh cho Claude CLI điều tra tận gốc nguyên nhân vì sao fix nhiều lần mà vẫn không tự động gọi Advisor.

---

## 2. Bóc trần Căn nguyên Gốc rễ (Root Cause Analysis từ Claude CLI)

### A. Lỗ hổng 1: "Vá trên giấy" (Soft Prompt Rules) chịu thua Suy hao Ngữ cảnh (Prompt Attenuation)
- Mọi nỗ lực trước đây chỉ là thêm tài liệu (SKILL.md, MEMORY.md, USER.md, prompt guidelines).
- Bản chất của LLM Coordinator (Gemini / Claude / Omni-Worker): Khi context dài ra (>50k tokens), các chỉ thị prompt mềm bị suy hao trọng số chú ý (Attention Drift). Khi User hỏi một câu hỏi gợi mở hoặc phản biện kỹ thuật, model lập tức kích hoạt thiên kiến trả lời trực tiếp (Immediate next-token generation bias) — lao vào giải thích bằng chính giọng của mình mà không dừng lại để gọi tool.

### B. Lỗ hổng 2: Plugin Guard chỉ chặn Tool Calls, hoàn toàn MÙ với Final Text Response
- Hệ thống bảo vệ farm (`farm-coordinator-guard`) hoạt động rất hiệu quả ở hook `pre_tool_call`: chặn lệnh ADB sai serial, chặn quét đĩa diện rộng, chặn sửa file vùng cấm.
- **Điểm mù chí mạng:** Khi Coordinator trả lời thẳng bằng Text chat cho User (Final Response):
  - Lượt phát ngôn này **KHÔNG gọi bất kỳ tool nào**.
  - Do đó, `pre_tool_call` không bao giờ được kích hoạt trên text trả lời trực tiếp!
  - Plugin `farm-coordinator-guard` hoàn toàn không có hook nào (như `transform_llm_output` hay pre-send interceptor) để kiểm duyệt text cuối trước khi gửi về Telegram.

### C. Lỗ hổng 3: Thiên kiến Né tránh Độ trễ (Latency Avoidance Bias)
- Sol Web High (`:20129 review` / `gpt-web-sol`) là reasoning model qua web pool, TTFT mất 15s – 35s.
- Coordinator từng chứng kiến timeout hoặc sợ treo phiên, nên hình thành phản xạ né tránh ngầm trong suy luận: tự trả lời cho nhanh thay vì kiên nhẫn đợi stream Sol trả về.

---

## 3. Bản vẽ Giải pháp Khắc phục Triệt để (Mechanical Enforcement)

### Chốt chặn 1: Kỷ luật Thao tác Pre-Send Invariant cho Coordinator
- Khi nhận diện User message có Advice Intent:
  - **CẤM PHÁT NGÔN CUỐI TURN (Final Text Response) nếu chưa có output từ tool `consult_advisor.py`**.
  - Bắt buộc gọi `consult_advisor.py` (hoặc direct `review` endpoint trên :20129) trong tool call ĐẦU TIÊN của turn, sau đó mới tổng hợp kết quả Dual-Answer.

### Chốt chặn 2: Mechanical Auto-Append Hook trong Plugin Guard
- Tích hợp hàm `ensure_dual_answer(message, response)` từ `scripts/advisor_consult.py` vào plugin hook của Hermes:
  - Khi user input match `classify_advice_intent`:
  - Nếu response text thiếu khối `--- Advisor (`, hook tự động thực thi truy vấn và nối khối Advisor vào đuôi response trước khi emit ra client.
