# Kiến Trúc Bơm Ngữ Cảnh Phiên Cho Advisor Sol (Session Context Enrichment & Prompt Packing)

## 1. Bản chất vấn đề Context Starvation của Advisor Web Pool
- Advisor Sol (`gpt-web-sol` trên port 20129) là cụm tài khoản ChatGPT-Web pool hoạt động dạng **Stateless HTTP API**, không lưu session context giữa các request.
- Nếu chỉ bốc duy nhất tin nhắn gần nhất của Operator (ví dụ: *"sao lại thế?"*, *"có nên nâng cooldown không?"*) gửi sang, Advisor hoàn toàn không biết farm đang chạy ở máy nào, nick nào, vừa thao tác gì, dẫn tới hiện tượng **trả lời cụt lủn, ngây ngô và hoàn toàn lệch pha với diễn biến phiên**.

---

## 2. Kiến trúc giải pháp 4 tầng (Đã nghiệm thu qua Claude Sonnet 5.5)

### Tầng 1: Trích xuất hiện trường & Tóm tắt hội thoại (`Hermes/agent/advisor_context.py`)
- **`infer_field_ctx(messages)`**: Quét ngược toàn bộ messages (từ tin nhắn mới nhất) bằng regex an toàn:
  * Máy: `(?:máy|machine)\s*#?(\d+)`
  * Nick: `(?<![\w@])@([a-zA-Z0-9_.]{2,32})` (dùng negative lookbehind để chặn bắt nhầm địa chỉ email).
  * Serial: `(?:serial|thiết bị|device)\s*[:=]?\s*(?=[a-zA-Z0-9]*\d)([a-zA-Z0-9]{8,24})\b` (lookahead `(?=[a-zA-Z0-9]*\d)` bắt buộc có ít nhất 1 chữ số để hỗ trợ serial alphanumeric như `R58N12ABCDE`, đồng thời chặn triệt để false-positives từ log ADB như `device unauthorized`, `device offline`, `device connection lost`).
- **`build_session_briefing(messages)`**:
  * Lấy tối đa 5 turns gần nhất (`user` và `assistant`). Bỏ tin nhắn user cuối nếu nó trùng với câu hỏi hiện tại.
  * Với assistant message có tool calls, rút gọn thành `ran: tool1, tool2 | content`.
  * Rút gọn mỗi turn $\le 280$ ký tự qua `_clip_text`.
  * Trần cứng tổng briefing: $\le 1.500$ ký tự (nếu vượt quá, tự động loại bỏ turn cũ nhất trước).

### Tầng 2: Kết nối Conversation Loop & Tool Schema (`conversation_loop.py` & `advisor_tool.py`)
- Trong `_consult_advisor_once`: Nhận danh sách `messages` của conversation loop, bọc `try/except` gọi `build_session_briefing` để lấy `field_context` và `session_briefing`.
- Trong `advisor_tool.py`:
  * Mở rộng `advisor_consult(..., session_briefing=None, field_context=None)`.
  * Gói vào payload gửi sang endpoint advisor, tương thích ngược 100% với các caller cũ.

### Tầng 3: Đóng gói Prompt 5 Tầng & Bảo toàn Câu hỏi (`consult_advisor.py`)
- **`build_advisor_prompt(query, current_state="", briefing="", field=None)`**:
  * Khung 5 tầng chuẩn:
    1. `[Bối cảnh hiện trường]`: Máy, Nick, Serial.
    2. `[Diễn biến phiên làm việc gần nhất]`: Briefing $\le 1.500$ chars.
    3. `[Trạng thái hiện tại của Coordinator]`: State $\le 1.000$ chars.
    4. `[Câu hỏi tư vấn của Operator]`: Query $\le 1.500$ chars.
    5. `[Yêu cầu]`: Chỉ thị đóng vai Solution Architect phản biện độc lập.
  * **Thuật toán co gọn briefing động (Dynamic Truncation - Chống cắt đuôi câu hỏi)**:
    - Tính toán ngân sách khả dụng: `avail = max(0, MAX_PROMPT_CHARS - len(field) - len(state) - len(query) - len(req) - 50)`.
    - Cắt tỉa các dòng cũ nhất của `briefing` nếu vượt ngân sách.
    - **TUYỆT ĐỐI KHÔNG CẮT ĐUÔI PROMPT**: Bảo toàn 100% nội dung câu hỏi và yêu cầu của Operator.

---

## 3. Kỷ luật An Toàn & Redaction (Bảo Mật Nghiêm Ngặt)
1. **Redact TRƯỚC KHI Clip/Truncate**:
   - Secret (`sk-`, `ghp_`, `AKIA`, `Bearer`, `JWT`, `password=`, `token=`) phải được thay thế bằng `[REDACTED]` trước khi thực hiện cắt ngắn chuỗi. Nếu cắt trước mới redact, mảnh secret bị chém ngang sẽ mất từ khóa nhận diện và lọt ra ngoài.
2. **Tương thích Python 3.11+ Regex**:
   - Không đặt cờ toàn cục `(?i)` ở giữa biểu thức regex (gây lỗi `re.error: global flags not at the start of the expression`). Phải dùng cờ `re.IGNORECASE` hoặc danh sách pattern phân rã.
3. **Phủ kín Dict Keys & Quoted JSON**:
   - Redaction cho dict phải kiểm tra substring `any(sk in norm_key for sk in _SECRET_KEYS)` để bắt trọn các key có tiền tố như `MY_API_KEY`, `GITHUB_TOKEN`.
   - Bao phủ các cặp `"key": "value"` trong JSON string cho cả `cookie`, `authorization`, `secret`.
4. **Che Giấu Cookie Toàn Dòng (Multi-Pair Cookie Leak)**:
   - Header Cookie thường chứa nhiều cặp phân tách bởi chấm phẩy (`Cookie: a=1; b=2; c=3`). Regex key-value `[^\s,;]+` chỉ che được cặp đầu `a=1` và làm lộ các session cookie nhạy cảm phía sau (`sid_tt=...`, `sessionid=...`). Bắt buộc dùng pattern riêng `\bcookie\s*[:=]\s*[^\r\n]+` để che sạch toàn bộ dòng.
5. **Che Toàn Bộ Credential Của Authorization (Không Chỉ Riêng Bearer)**:
   - Header `Authorization: Basic <base64>` hay các scheme khác cần được che phủ toàn bộ credential phía sau bằng `\bauthorization\s*:\s*[^\r\n,;]+`, tránh chỉ che chữ `Basic` mà để lộ payload.
6. **Cập Nhật Metrics Dưới Lock**:
   - Trong `conversation_loop.py`, tuyệt đối không tăng trực tiếp `ADVISOR_METRICS[...] += 1` mà phải gọi qua `_advisor_metric_inc(name)` để bảo đảm thread-safety dưới `_ADVISOR_METRICS_LOCK`.
