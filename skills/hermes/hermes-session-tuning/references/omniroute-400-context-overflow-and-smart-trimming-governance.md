# OmniRoute 400 Context Overflow & Mechanical Trimming Governance

## 1. Sự cố Kẹt 400 Context Overflow & Combo Cascading
- **Nguyên nhân gốc:** Khi một prompt/turn đơn lẻ bị phình to đột biến (do tool outputs lớn như terminal log, grep, file dump), context vượt trần 1.048.576 tokens của Google Gemini Flash trước khi kịp kích hoạt compressor.
- **Lỗ hổng Combo Cascade trong `combo.ts`:**
  - Logic cũ: `!isContextOverflow400(errorText)` khiến lỗi context overflow bị coi là có thể fallback được.
  - Hệ quả: Router tiếp tục ném payload > 1M tokens sang tất cả các node cùng model trong combo pool, làm bẩn toàn bộ pool tài khoản.
- **Bản vá chuẩn:**
  1. Thêm `/\binput token count exceeds\b/i` vào `isContextOverflow400`.
  2. Bổ sung `errorText` vào `isInputBoundRequestFailure(structuredError, errorText)`.
  3. Khi phát hiện `isInputBoundFailure` trên pool homogeneous (dàn node cùng model), router **ngắt ngay lập tức (`return { ok: false, response: result }`)**, không fallback, không trừ điểm node.

## 2. Cơ chế "Tỉa khôn" (Structural Mechanical Trimming) vs "Nén ngu" (LLM Summarization)
- **Nén ngu (LLM Summarization):** Gọi model tóm tắt đoạn giữa thành văn xuôi làm mất sạch chi tiết kỹ thuật (IP, port, file path, error trace) $\to$ Agent bị Completion Bias, ảo giác tưởng xong việc và phá vỡ Prompt Cache của Gemini.
- **Tỉa khôn (Structural Mechanical Trimming):**
  - Giữ nguyên 100% tin nhắn của User và lý luận của AI.
  - Bảo vệ tối thiểu 3 tool outputs gần nhất $\le 50.000$ ký tự.
  - Các tool outputs cũ trong quá khứ chỉ giữ lại 2.000 ký tự đầu/cuối kèm marker `...[truncated]`.
  - Context giảm từ 900k xuống ~100k tokens ngay lập tức mà không mất trí nhớ logic.

## 3. Quy tắc An toàn khi Build / Restart OmniRoute (Chống Sập Watchdog)
- **CẤM TUYỆT ĐỐI:** Chạy `npm run build:backend` hoặc `npm run build` với timeout ngắn (<180s) rồi kill process khi chưa xác nhận file `BUILD_ID`.
- **Hậu quả:** Next.js bị xóa thư mục build cũ nhưng chưa kịp ghi `BUILD_ID` $\to$ `next start` crash code 1 mỗi 65s $\to$ Watchdog rơi vào flapping loop.
- **Quy trình chuẩn:**
  1. Chỉ restart khi build hoàn tất exit code 0 và file `.build/next/BUILD_ID` tồn tại.
  2. Watchdog phải kiểm tra sự tồn tại của `BUILD_ID` trước khi thực hiện `Start-OmniRoute`.

## 4. Minh bạch Kết quả Hội đồng Cố vấn (Advisor Council Transparency)
- Khi pipeline S1 hoàn tất, BẮT BUỘC liệt kê tường minh kết quả của từng cố vấn:
  * Gemini Argon: [OK/FAIL/TIMEOUT, lý do]
  * Claude Sonnet: [OK/FAIL/TIMEOUT, lý do]
  * Sol Web: [OK/FAIL/TIMEOUT, lý do]
  * Tỷ lệ đồng thuận (3/3 hay 2/3) và lý do chọn bản vá cuối cùng.
- CẤM nói chung chung "đã qua pipeline" mà giấu biểu quyết của Cố vấn.
