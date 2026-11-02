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

### B. Lỗ hổng Combo Cascade Poisoning trong OmniRoute (`combo.ts` & `comboPredicates.ts`):
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
2. **Kẽ hở `isInputBoundRequestFailure`**:
   - `isInputBoundRequestFailure(error)` chỉ kiểm tra `error.code` và `error.type` dạng chuỗi (tìm `context_length_exceeded`). Vì Google trả về `code: 400` dạng số và status `INVALID_ARGUMENT`, hàm trả về `false`.
   - Kết quả: Biến `isInputBoundFailure` tại dòng 2148 của `combo.ts` bị `false`, router không kích hoạt nhánh ngắt sớm trên homogeneous remainder pool.
3. **Bug Logic Fast-Fail Trong Router (`open-sse/services/combo.ts`)**:
   - Đoạn code kiểm tra dừng combo khi gặp HTTP 400 (dòng 2234) có điều kiện: `!isContextOverflow400(errorText)`.
   - Khi lỗi là Context Overflow, `isContextOverflow400` trả về `true` $\implies$ phủ định `!isContextOverflow400` thành `false`!
   - Hậu quả: Router không coi đây là lỗi client cần dừng ngay, mà coi là lỗi có thể fallback tiếp được, dẫn đến việc mang nguyên vẹn prompt quá khổ ném lần lượt qua tất cả các account còn lại trong pool (`4c8a6e77...`, `ff22bcba...`) cho đến khi hết 20 lượt retry.
   - Kết quả: Toàn bộ dàn tài khoản trong pool đều bị đánh dấu `failed / 400 UPSTREAM`, gây hiểu lầm là dàn account bị Google khóa hoặc chết proxy hàng loạt.
4. **Thiếu Regex Match Trong `isContextOverflow400`**:
   - Thiếu mẫu đặc thù của Google Cloud Code Antigravity: `The input token count exceeds the maximum number of tokens allowed 1048576`.

---

## 3. Bản Vá Đã Áp Dụng Thực Tế Trên Mã Nguồn OmniRoute

1. **`open-sse/services/combo/comboPredicates.ts`**:
   * Thêm pattern `/\binput token count exceeds\b/i` vào `isContextOverflow400`:
     ```typescript
     export function isContextOverflow400(errorText: string | null | undefined): boolean {
       const text = String(errorText || "");
       if (!text) return false;
       return (
         /\bcontext.*(?:length_exceeded|too long|overflow|exceeded|window|limit)\b/i.test(text) ||
         /exceeds.*context/i.test(text) ||
         /your input exceeds/i.test(text) ||
         /\binput token count exceeds\b/i.test(text) ||
         CONTEXT_OVERFLOW_PATTERNS.some((p) => p.test(text))
       );
     }
     ```
   * Mở rộng `isInputBoundRequestFailure(error, errorText)`:
     ```typescript
     export function isInputBoundRequestFailure(
       error?: { code?: string | null; type?: string | null },
       errorText?: string | null
     ): boolean {
       const code = typeof error?.code === "string" ? error.code.toLowerCase() : "";
       const type = typeof error?.type === "string" ? error.type.toLowerCase() : "";
       return (
         INPUT_BOUND_ERROR_CODES.has(code) ||
         type === "context_length_exceeded" ||
         isContextOverflow400(errorText)
       );
     }
     ```

2. **`open-sse/services/combo.ts`**:
   * Tại dòng 2148, truyền `errorText` vào hàm kiểm tra:
     ```typescript
     const isInputBoundFailure =
       isInputBoundRequestFailure(structuredError, errorText) && remainderIsHomogeneous;
     ```
   * **Hiệu lực cơ học:** Khi một request gửi vào combo `ag-gemini-pool-3` (pool toàn bộ là `gemini-3.8-flash-tiered`) bị Google reject với lỗi `The input token count exceeds...`, router nhận diện ngay đây là `isInputBoundFailure` trên homogeneous pool, **lập tức ngắt chuỗi fallback (`return { ok: false, response: result }`) ngay tại node đầu tiên**, không thử sang 19 node còn lại, và **không phạt điểm circuit breaker** của dàn tài khoản.

---

## 4. Phân Biệt Nén Ngu (LLM Summarization) vs Tỉa Khôn (Mechanical Trimming)

- **Nén ngu (LLM Summarization của Hermes mặc định):**
  * Gọi LLM tóm tắt lại các turn cũ thành đoạn văn xuôi `[CONTEXT COMPACTION — REFERENCE ONLY]`.
  * **Hại:** Rơi rụng path, port, biến số, log lỗi thực tế; gây ra **Completion Bias** (AI tự ảo giác là việc đã xong để làm vừa lòng User); đồng thời làm **vỡ Prompt Cache prefix** của Gemini (buộc phải cache lại từ đầu tốn tiền và chậm).
- **Tỉa khôn (Structural Mechanical Truncation):**
  * Giữ nguyên 100% lời nói của User, chỉ đạo của Coordinator và lý luận của AI.
  * Chỉ "rút ruột" các `tool_result` cũ trong quá khứ (lệnh `terminal`, `read_file` chạy từ 10–20 turn trước dài 50k ký tự): chỉ giữ 3 dòng đầu + `[... output trimmed ...]` + 3 dòng cuối + exit code.
  * Giảm ngay 80% token mà giữ 100% mạch suy nghĩ, không bao giờ bị dính lỗi 400.

---

## 5. Quy Trình Triage Chuẩn O(1) Cho Người Vận Hành
1. **Kiểm Tra Trực Tiếp Log Thật Của OmniRoute**:
   - File log: `C:\Users\Kibe\AppData\Roaming\omniroute\logs\omniroute-stdout.log`.
   - Tìm cụm `Status: 400` và bóc trường `Body:` trong log để xem thông điệp chính xác của upstream.
   - CẤM đoán mò hoặc kết luận vội là tài khoản chết, proxy lỗi khi chưa đọc nội dung Body upstream.
2. **Xác Định Nguồn Phát Request & Xử Lý**:
   - Tìm session / tool / script đang đẩy request > 1M tokens vào OmniRoute.
   - Thực hiện reset session (`/new`), nén context (context compression), hoặc loại bỏ payload/file nhồi quá lớn.
   - Khi context thu về dưới 1M tokens, các node trong pool Antigravity sẽ trở lại HTTP 200 OK ngay lập tức mà không cần can thiệp tài khoản.
