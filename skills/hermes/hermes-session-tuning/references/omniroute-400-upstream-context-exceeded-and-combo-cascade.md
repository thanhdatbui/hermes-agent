# OmniRoute 400 Upstream Error & Combo Cascading Invariant

## 1. Bối Cảnh & Hiện Tượng
- Trên Dashboard OmniRoute (`192.168.110.123:20128` / `:20129`), bảng lịch sử request ghi nhận một chuỗi dài các node / model attempts trả về mã **HTTP 400** hoặc **499**, trạng thái `failed`.
- Các node lần lượt bị đánh dấu failed liên tục: ví dụ `gemini-3.8-flash-tiered` trên node `4c8a6e77...`, `ff22bcba...`, `1ebe3db9...` thuộc combo `ag-gemini-pool-3`.
- Người vận hành thắc mắc: **"Tại sao client đã set ngưỡng nén context 600k (threshold 0.6) mà upstream Google vẫn bị vượt trần 1.048.576 tokens (>1M)?"**

---

## 2. Nguyên Nhân Kỹ Thuật Cốt Lõi (Root Causes)

### A. Tại sao ngưỡng nén 600k không chặn được tràn 1M?
1. **Cơ chế nén chạy giữa các turn (Inter-turn Compression):**
   - Compressor của Hermes Gateway chỉ kích hoạt **sau khi kết thúc một turn** để chuẩn bị cho turn tiếp theo.
2. **Hiện tượng "Nhảy cóc" trong một Turn đơn lẻ (Single-turn Output Jump):**
   - Session đang ở mức an toàn (~500k tokens).
   - Trong turn đó, Agent gọi các tool trả về output khổng lồ (dump log, đọc file lớn, subagent gom toàn bộ kết quả, hoặc cào HTML).
   - Toàn bộ output được cộng dồn ngay lập tức vào tin nhắn tiếp theo gửi lên model. Context nhảy vọt từ ~500k lên thẳng **1.047.533 tokens** rồi vượt ngưỡng **1.048.576 tokens** TRƯỚC KHI compressor kịp chạy.
3. **Kẽ hở Parallel Tool Calls (Cộng dồn song song):**
   - Dù mỗi tool call được clamp độc lập (ví dụ 50k ký tự), nếu Agent gọi song song 10–20 tool calls trong 1 turn, tổng dung lượng kết quả vẫn bơm thêm hàng trăm nghìn tokens làm nổ context.

### B. Lỗ hổng Combo Cascade Poisoning trong OmniRoute (`combo.ts`):
1. **Upstream Google Error Signature:**
   ```json
   {
     "error": {
       "code": 400,
       "message": "The input token count exceeds the maximum number of tokens allowed 1048576.",
       "status": "INVALID_ARGUMENT"
     }
   }
   ```
2. **Bug Logic Fast-Fail Trong Router (`open-sse/services/combo.ts`)**:
   - Đoạn code kiểm tra dừng combo khi gặp HTTP 400 có điều kiện: `!isContextOverflow400(errorText)`.
   - Khi lỗi là Context Overflow, `isContextOverflow400` trả về `true` $\implies$ phủ định `!isContextOverflow400` thành `false`!
   - Hậu quả: Router không coi đây là lỗi client cần dừng ngay, mà coi là lỗi có thể fallback tiếp được, dẫn đến việc mang nguyên vẹn prompt quá khổ ném lần lượt qua tất cả các account còn lại trong pool (`4c8a6e77...`, `ff22bcba...`) cho đến khi hết 20 lượt retry.
   - Kết quả: Toàn bộ dàn tài khoản trong pool đều bị đánh dấu `failed / 400 UPSTREAM`, gây hiểu lầm là dàn account bị Google khóa hoặc chết proxy hàng loạt.
3. **Thiếu Regex Match Trong `CONTEXT_OVERFLOW_PATTERNS`**:
   - Regex trong `accountFallback.ts` thiếu mẫu đặc thù của Google Cloud Code Antigravity: `The input token count exceeds the maximum number of tokens allowed 1048576`.

---

## 3. Kiến Trúc Khắc Phục Triệt Để (Thống Nhất Cùng Hội Đồng Cố Vấn)

### Tầng 1: OmniRoute Gateway (Dập tắt thác đổ & Bảo vệ Node)
1. **Nhận diện chính xác mẫu lỗi Google:**
   - Bổ sung pattern vào `CONTEXT_OVERFLOW_PATTERNS`:
     `/\binput token count exceeds\b/i` hoặc `/\bexceeds the maximum number of tokens allowed\b/i`.
2. **Dập tắt Fallback trên cùng Model Pool:**
   - Khi gặp HTTP 400 có `isContextOverflow400(errorText) === true`, nếu target kế tiếp trong Combo có context window tương đương hoặc nhỏ hơn ($\le 1\text{M}$), **lập tức dừng fallback (`return { ok: false, response: result }`)**.
   - Chỉ cho phép fallback nếu target tiếp theo có context window lớn hơn hẳn (ví dụ Gemini Pro 2M).
3. **Bảo vệ sức khỏe Node (Zero-Penalty):**
   - Lỗi Context Overflow là lỗi **Request-Level (do client)**, tuyệt đối không trừ điểm sức khỏe, không kích hoạt circuit breaker làm phạt node.

### Tầng 2: Hermes Client & Agent Runtime (Chặn từ gốc)
1. **Trần dung lượng tổng cho Tool Output theo Turn (Per-turn Aggregate Cap):**
   - Không chỉ clamp từng tool độc lập ($\le 50\text{k}$ chars), bắt buộc phải clamp **tổng kích thước tất cả tool results trong 1 turn** ($\le 100\text{k}$ chars / ~25k tokens) để bịt kẽ hở parallel tool calls.
2. **Pre-flight Token Estimate & Emergency Compaction:**
   - Trước khi dispatch request sang router, nếu ước tính `prompt_tokens > 900.000`, client phải kích hoạt ngay **Emergency Sliding Window / Pruning** (tỉa bớt tool output cũ ở giữa history) thay vì ném request quá khổ lên upstream.
3. **Chống nhiễm độc lịch sử (Anti-History Poisoning):**
   - Khi nhận mã 400 Context Overflow trả về từ gateway, Agent Runtime phải nhận diện mã lỗi có cấu trúc để tự động prune history trước khi retry, tránh vòng lặp retry vô tận với context bị kẹt > 1M.

---

## 4. Quy Trình Triage & Khắc Phục Chuẩn O(1)
1. **Kiểm Tra Trực Tiếp Log Thật Của OmniRoute**:
   - File log: `C:\Users\Kibe\AppData\Roaming\omniroute\logs\omniroute-stdout.log`.
   - Tìm cụm `Status: 400` và bóc trường `Body:` trong log để xem thông điệp chính xác của upstream.
   - CẤM đoán mò hoặc kết luận vội là tài khoản chết, proxy lỗi khi chưa đọc nội dung Body upstream.
2. **Xác Định Nguồn Phát Request & Xử Lý**:
   - Tìm session / tool / script đang đẩy request > 1M tokens vào OmniRoute.
   - Thực hiện reset session (`/new`), nén context (context compression), hoặc loại bỏ payload/file nhồi quá lớn.
   - Khi context thu về dưới 1M tokens, các node trong pool Antigravity sẽ trở lại HTTP 200 OK ngay lập tức mà không cần can thiệp tài khoản.
