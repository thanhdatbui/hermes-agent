# On-Demand Advisor Sol & JSON Parsing vs 45s Timeout Resolution (2026-10-20)

## 1. Bối cảnh & Yêu Cầu Của Operator
- **Chuyển hẳn sang On-Demand:** Operator yêu cầu tắt vĩnh viễn cơ chế auto-append chèn đuôi Advisor Sol vào mọi câu hỏi chat thông thường. Advisor chỉ được kích hoạt khi Operator chủ động gọi (`gọi advisor`, `hỏi sol`, `gọi sol`, `sol thấy sao`, `nhờ sol review`, `sol lên plan`) hoặc khi cần phản biện một bản thiết kế/plan lớn trước khi thi công.
- **Giải mã bí ẩn lỗi "Báo 45s dồn dập ở mọi câu hỏi":** Dù đã tăng timeout ở script nhiều lần, Coordinator ở các session khác vẫn liên tục báo lỗi timeout quá 45s.

---

## 2. Phân Tích Gốc Rễ Kỹ Thuật (Root Cause)

### A. Bẫy Timeout Ảo do Lỗi Parse JSON (`response content did not contain a JSON object`)
- Trong `Hermes/tools/advisor_tool.py`, hàm `_first_json_object` bắt buộc Sol phải trả về JSON có cấu trúc.
- Khi Sol Web trả về text Markdown thông thường, hàm không trích xuất được JSON nên quăng lỗi `response content did not contain a JSON object` và gán trạng thái `status = "error"`.
- Hermes Core sau đó gắn câu thông báo mặc định: `Advisor: unavailable (Sol / review timeout hoặc pool limit...)`.
- Coordinator đọc thấy thông báo này, do memory có mốc 45s nên **tự suy diễn và báo cáo với Operator là "bị quá 45s"**, dù thực tế request chỉ chạy mất 15s–23s và thành công ở tầng mạng!

### B. Bẫy Cắt Cụt Ngữ Cảnh (Context Starvation & Clip Text)
- Trước đây `advisor_context.py` cắt cứng mỗi turn còn 280 ký tự (`head_len=180`, `tail_len=97`), khiến các chi tiết trao đổi kỹ thuật (như thảo luận với Claude) bị chém bay mất ruột, chỉ còn lại mẩu câu nhắc tên Claude làm Sol hiểu lầm là bắt buộc phải có biên bản bàn giao với Claude.
- Đã nâng trần: `MAX_MSG_CHARS = 800`, `MAX_BRIEF_CHARS = 4000` (giữ trọn vẹn ngữ cảnh 5 turns gần nhất).

---

## 3. Kiến Trúc Chuẩn Hóa Đã Triển Khai

1. **Cơ chế On-Demand tại `agent/conversation_loop.py`:**
   ```python
   _ADVISOR_EXPLICIT_TRIGGERS = ("gọi advisor", "hỏi sol", "gọi sol", "sol thấy sao", "nhờ sol review", "sol lên plan")

   def _is_advice_request(message: Any) -> bool:
       if not isinstance(message, str): return False
       lowered = " ".join(message.split()).casefold()
       return any(re.search(rf"(?<!\w){re.escape(t)}(?!\w)", lowered) is not None for t in _ADVISOR_EXPLICIT_TRIGGERS)
   ```
   Các câu hỏi thường (`có nên...?`, `nên làm gì...?`, `tư vấn...`) trả về `False`, triệt tiêu hoàn toàn tình trạng chen ngang.

2. **Hỗ trợ Song Song JSON + Markdown trong `tools/advisor_tool.py`:**
   - System prompt ép Sol: `You must return ONLY a JSON object with keys: recommendation, reasoning, plan.`
   - Timeout nâng lên `DEFAULT_TIMEOUT = 140s`, `FIRST_TOKEN_TIMEOUT = 80s`, `IDLE_TOKEN_TIMEOUT = 20s`.
   - Hàm `_read_content` tự động xử lý cả HTTP JSON response lẫn SSE streaming chunks.

3. **Phân Định Tuyệt Đối 2 Thực Thể Sol:**
   - **Sol Advisor:** Cố vấn chiến lược, chạy on-demand qua `advisor_tool.py` và `consult_advisor.py` (tối đa 4.000 ký tự context briefing).
   - **Sol Reviewer:** Quan tòa độc lập chấm điểm diff cuối phiên qua `closeout_gate.py` và `sol_payload_guard.py` (kẹp cứng 40 KB diff, timeout 300s).
