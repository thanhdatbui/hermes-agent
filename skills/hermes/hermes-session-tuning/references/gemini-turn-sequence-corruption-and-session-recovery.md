# Sự Cố Lệch Cấu Trúc Turn Gemini HTTP 400 & Quy Trình Khôi Phục Session Qua session_search

## 1. Hiện Trường Sự Cố (07/10/2026)
- **Session gặp nạn**: `@session:default/20261006_223015_31af483f` (Topic "Tiến trình hotma", 123 tin nhắn).
- **Triệu chứng Telegram**:
  1. Agent xuất hiện lỗi raw JSON quăng thẳng vào khung chat:
     ```json
     HTTP 400: [400]: {
       "error": {
         "code": 400,
         "message": "Please ensure that function call turn comes immediately after a user turn or after a function response turn.",
         "status": "INVALID_ARGUMENT"
       }
     }
     ```
  2. Sau khi User nhắn tiếp để phản hồi/chửi, Agent tiếp tục rơi vào trạng thái treo ngâm stream chunk 6 - 12 phút mỗi lượt:
     `⌛ Working — 6 min — iteration 0/200, waiting for stream response (4s, no chunks yet)`
     hoặc `iteration 5/200, receiving stream response`.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)

### 2.1. Quy chuẩn nghiêm ngặt của Google Gemini API (Strict Turn Alternating Schema)
- Khác với OpenAI API chấp nhận danh sách message linh hoạt hơn, Google Gemini API (và các provider bọc Gemini như Antigravity / OmniRoute) bắt buộc cấu trúc turn phải luân phiên tuyệt đối:
  - `user` turn $\rightarrow$ `model` turn (chứa `functionCall`).
  - Sau `functionCall` BẮT BUỘC phải là `function` (chứa `functionResponse`).
  - Sau `functionResponse` mới được phép là `model` turn kế tiếp.
- Tuyệt đối CẤM:
  - 2 lượt `model` turn liên tiếp.
  - Lượt `model` có `functionCall` nhưng không có `functionResponse` ngay sau đó.
  - Lượt `user` chen ngang giữa `functionCall` và `functionResponse`.

### 2.2. Cơ chế gây rách Turn trong Hermes Agent & Bẫy Sanitizer
- **Tool result stripping & Orphaned tool_calls (`context_compressor.py:_sanitize_tool_pairs`)**:
  - Khi nén context trên session dài (>100 turns), compressor cắt bớt middle window.
  - Hàm `_sanitize_tool_pairs()` phát hiện tool results bị drop và strip `tool_calls` khỏi assistant message, gán fallback `content = "(tool call removed)"`.
  - Nếu assistant message này đứng kề một assistant message khác hoặc đứng trước một summary turn `role="assistant"`, thứ tự luân phiên turn bị phá vỡ.
- **Tại sao CẤM tăng `compression.threshold` để tránh nén**:
  - Model chính (Gemini) context 1M, `threshold: 0.3` nén ở ~300k tokens.
  - Các worker subagent (GPT-5.6 luna/terra) có context trần cứng **372k tokens** (Codex 272k tokens).
  - Nếu nâng threshold lên 0.45 hay 0.5 (450k-500k), context sẽ vượt qua 372k TRƯỚC KHI nén kịp chạy $\rightarrow$ Worker subagent bị ngọng / crash toàn bộ. Do đó `threshold: 0.3` là bất biến.
- **Rách context do ngắt turn / crash giữa chừng**:
  - Khi agent đang thực hiện chuỗi tool call mà gặp network socket timeout / drop stream từ upstream proxy hoặc vi phạm guardrails giữa chừng.
  - Turn context bị ghi dở dang vào SQLite `state.db` (thiếu tool response tương ứng cho tool call đã ghi nhận, hoặc assistant turn bị nhân đôi).
- Khi user gửi tin nhắn mới, Hermes đóng gói toàn bộ message history gửi lên upstream. Gemini phát hiện schema không hợp lệ và quăng lỗi HTTP 400 `INVALID_ARGUMENT`.

### 2.3. Bẫy treo Stream "Waiting for chunks yet"
- Khi session đã bị lỗi 400, Hermes không tự động reset hay sửa turn bị rách trong SQLite.
- Ở các turn tiếp theo, client gửi request lên upstream nhưng do stream handshake bị lỗi hoặc backend retry không nhận được chunk đầu tiên, agent ngâm đợi chunk (`waiting for chunks yet`) kịch trần timeout (6 - 12 phút), khiến User thấy bot hoàn toàn bị "đơ" hoặc "điên".

---

## 3. Quy Trình Khôi Phục Chuẩn (Recovery Workflow)

### Bước 1: DỪNG NGAY việc nhắn tin vào Session cũ
- Cố gắng chat tiếp vào thread/session đã bị rách turn là vô ích: 100% request tiếp theo đều gửi kèm history lỗi và tiếp tục bị Gemini reject HTTP 400 hoặc treo stream.

### Bước 2: Khởi tạo Session mới sạch (`/new`)
- Dùng lệnh `/new` trên Telegram hoặc mở một thread/phiên mới để có một message store hoàn toàn sạch, reset API payload về ~24k tokens ban đầu.

### Bước 3: Dùng `session_search` để cứu hộ (Salvage) Context & Task dở dang
Tại session mới, Coordinator BẮT BUỘC thực hiện quy trình phục hồi 3 bước:
1. **Tìm kiếm session cũ**:
   - Dùng `session_search(query="<từ khóa hoặc mã lỗi>")` để lấy `session_id` và `match_message_id`.
   - Hoặc nếu biết `session_id`: gọi `session_search(around_message_id=..., session_id="...", window=10)`.
2. **Trích xuất 3 thông tin cốt lõi**:
   - **Yêu cầu gốc của User**: User muốn làm gì trước khi bị kẹt?
   - **Hiện trường kỹ thuật & Việc đã làm**: Tool nào đã chạy xong, file/acc nào đang xử lý?
   - **Nút thắt gây lỗi**: Điểm nghẽn khiến bot cũ kẹt là gì (ví dụ: thiếu API lấy OTP mail domain, timeout script...)?
3. **Báo cáo và tiếp quản mượt mà**:
   - Trình bày ngắn gọn cho User: (a) Giải thích lỗi rách turn 400 của session cũ, (b) Tóm tắt task dang dở vừa vớt được từ `session_search`, (c) Đưa ra phương án giải quyết dứt điểm tại session mới mà không bắt User phải nhắc lại từ đầu.
