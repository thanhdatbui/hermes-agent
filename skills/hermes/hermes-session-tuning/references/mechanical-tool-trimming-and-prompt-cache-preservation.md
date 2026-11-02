# Cơ Chế Tỉa Khôn Context (Mechanical Tool Output Trimming) vs LLM Summarization

## 1. Bản chất: Tại sao LLM Summarization mặc định bị coi là "Nén ngu"?
- Mặc định, Hermes nén context bằng cách gọi model phụ tóm tắt 30–50 turns cũ thành văn bản `[CONTEXT COMPACTION — REFERENCE ONLY]`.
- **Hậu quả 1 (Mất trí nhớ kỹ thuật & Báo cáo láo):**
  - Tóm tắt văn xuôi làm rơi rụng các thông số kỹ thuật cốt tử: đường dẫn file, exit code thực tế, IP, cổng, biến môi trường.
  - Đọc lại bản tóm tắt chung chung, Agent ở turn sau bị **Completion Bias**, tự suy diễn mọi thứ đã "xong / ổn định" và báo cáo láo với User.
- **Hậu quả 2 (Phá hủy Prompt Cache của Gemini):**
  - Prompt Caching của Google yêu cầu prefix token phải giữ **nguyên vẹn 100% từng byte**.
  - Khi tóm tắt văn xuôi viết lại đoạn giữa, prefix bị thay đổi hoàn toàn -> **Cache Miss 100%**, phản hồi chậm đi và hao quota gấp bội.

## 2. Cơ chế "Tỉa khôn" (Structural Mechanical Trimming)
- Trong 1 triệu tokens của session dài, 90% dung lượng nằm ở **phần ruột của các tool output cũ** (`terminal`, `read_file`, `inspect_machine`).
- Các lệnh đã chạy từ 10–20 turn trước thì chi tiết log bên trong không còn giá trị, Agent chỉ cần biết trạng thái thực thi.
- **Quy tắc tỉa khôn (Triển khai tại `open-sse/services/compression/lite.ts`):**
  1. **Lời nói giữ nguyên 100%:** Toàn bộ tin nhắn User, chỉ đạo Coordinator và suy luận của AI không bị tóm tắt, không suy diễn.
  2. **Bảo vệ cửa sổ làm việc gần nhất:** Giữ nguyên vẹn 3 tool messages gần nhất không bị cắt ngắn (chỉ clamp nếu vượt trần 50.000 chars).
  3. **Rút ruột các tool output cũ trong quá khứ:** Các tool results cũ hơn nếu vượt quá `MAX_TOOL_LENGTH` (2.000 chars) thì cắt gọn còn 2.000 chars kèm marker `...[truncated]`.
  4. **Kích hoạt Auto-Trigger tại Gateway:** Cấu hình `autoTriggerTokens: 800000`, `autoTriggerMode: "lite"` trong `key_value` SQLite để tự động kích hoạt tỉa khi prompt chạm 800k tokens.
- **Kết quả:** Context thu nhỏ từ 900.000 tokens về ~150.000 tokens trong 1ms, không mất chi tiết logic và không làm vỡ Prompt Cache.
