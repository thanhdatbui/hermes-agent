# OmniRoute Gemini Reasoning & Dynamic / Tiered Thinking Architecture

## 1. Bản chất Dynamic / Tiered Reasoning trên Google Gemini (Flash 3.7 / 3.8)
- **Chuẩn upstream Google (Cloud Code / Antigravity & AI Studio):**
  - **Dynamic / Tiered (Tự co giãn suy luận):** Cấu hình `generationConfig.thinkingConfig` có `thinkingBudget: -1` kèm `includeThoughts: true` (hoặc omit `thinkingBudget`). Model tự đánh giá độ khó của câu hỏi: câu dễ phản hồi nhanh (vài chục token thinking), câu khó tự đào sâu (hàng ngàn token).
  - **Fixed Budget (Khóa cứng trần suy luận):** Cấu hình `thinkingBudget > 0` (ví dụ 1024, 8192, 24576). Model bị ép trần số lượng token suy nghĩ.

## 2. Rào cản trong mã nguồn OmniRoute (`open-sse/translator/request/openai-to-gemini.ts`)
Hiện tại, OmniRoute **chưa hỗ trợ Dynamic/Tiered thinking** do translator tự động ép số token cụ thể:
1. **Khi client gửi `reasoning_effort: "auto"`:**
   - Trong `openai-to-gemini.ts`, `budgetMap["auto"]` map trực tiếp sang `highBudget = capThinkingBudget(model, 32768)` (với Flash là 24,576 tokens).
2. **Khi client gửi `"medium"` hoặc `"low"`:**
   - Map cứng sang 8,192 tokens hoặc 1,024 tokens.
3. **Khi client KHÔNG gửi `reasoning_effort` (bỏ trống):**
   - Translator kích hoạt nhánh default fallback:
     ```typescript
     result.generationConfig.thinkingConfig = {
       thinkingBudget: getDefaultThinkingBudget(model) || capThinkingBudget(model, 24576),
       includeThoughts: true,
     };
     ```
   - Trong `src/shared/constants/modelSpecs.ts`, `gemini-3.8-flash-tiered` có `defaultThinkingBudget: 8192`. OmniRoute tự động inject `thinkingBudget: 8192` vào payload gửi lên Google.
4. **Hệ quả:** Mọi request qua OmniRoute đều mang một con số `thinkingBudget > 0` cố định, Google buộc phải tuân theo số đó và tắt cơ chế Dynamic/Tiered tự cân chỉnh.

## 3. Đặc thù Opaque / Silent Thinking của dòng Flash trên Antigravity
- Trên backend Google Cloud Code (`daily-cloudcode-pa.googleapis.com` qua Antigravity):
  - Dòng **Flash (`gemini-3.7-flash-tiered`, `gemini-3.8-flash-tiered`)**: Google thực thi reasoning ngầm, trả về `usageMetadata.thoughtsTokenCount` và `thoughtSignature`, nhưng **KHÔNG stream raw text `thought: true`** trong `content.parts`. Do đó `reasoning_content` ở client luôn rỗng dù token suy luận vẫn được tính.
  - Dòng **Pro (`gemini-3.1-pro-high`)**: Google trả về đầy đủ block text `thought: true` hiển thị chuỗi suy nghĩ.

## 4. Thẩm định kiến trúc từ Sol Web (GPT-5.6 Sol) & Cạm bẫy `thinkingBudget: -1`
Khi tham vấn ý kiến kiến trúc với Sol Web (`chatgpt-web/gpt-5.6-sol-high` qua cổng `:20129`):
1. **Cạm bẫy `thinkingBudget: -1`:**
   - Tuyệt đối **KHÔNG NÊN** dùng `thinkingBudget: -1` làm mặc định. Nhiều backend của Google Cloud Code / Antigravity validate schema `thinkingBudget` là số nguyên không âm (`>= 0`).
   - Gửi `-1` có nguy cơ cao văng lỗi `400 INVALID_ARGUMENT: thinkingBudget must be >= 0`.
2. **Giải pháp chuẩn hóa an toàn nhất: OMIT `thinkingBudget`:**
   - Thay vì truyền `-1`, chỉ cần **bỏ hẳn key `thinkingBudget`** và chỉ gửi `includeThoughts: true`:
     ```json
     "thinkingConfig": {
       "includeThoughts": true
     }
     ```
   - Khi nhận payload này, engine Gemini 3.8 Flash bên dưới sẽ tự động chuyển sang chế độ Dynamic/Tiered (câu dễ nghĩ ít, câu khó nghĩ nhiều) mà hoàn toàn không lo dính lỗi schema 400.

## 5. Khuyến nghị Patch chuẩn trong OmniRoute (`open-sse/translator/request/openai-to-gemini.ts`)
Thay vì map `auto` sang `highBudget` (24,576 tokens) hay fallback nhét `defaultThinkingBudget`:
```typescript
if (body.reasoning_effort === "auto") {
  result.generationConfig.thinkingConfig = {
    includeThoughts: true,
    // Bỏ thinkingBudget để ủy quyền toàn quyền cho dynamic engine của upstream
  };
} else if (body.reasoning_effort) {
  // Map các mức cố định: none -> 0, low -> 1024, medium -> 8192, high -> highBudget
  ...
}
```
- **Kiểm tra `applyAntigravityGenerationDefaults` (`antigravity.ts` dòng 313):**
  Hàm này chỉ clamp `maxOutputTokens` khi `Number.isFinite(thinkingBudget) && thinkingBudget > 0`. Khi `thinkingBudget` bị omit (undefined), nó bỏ qua an toàn và không gây xung đột output limit.

## 6. Tham vấn kiến trúc & Audit qua Sol Web trực tiếp từ Coordinator
- **Cách gọi Sol an toàn qua allowlist Coordinator:**
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --text "<Nội dung tham vấn>" --system-prompt "<System prompt đóng vai Sol>"
  ```
- **Lưu ý Guard Terminal:**
  - Tuyệt đối không để chuỗi ký tự `>` (kể cả dấu mũi tên `->`) trong tham số lệnh terminal vì sẽ bị hook `guard_coordinator_terminal` chặn với lỗi redirect file. Hãy dùng từ ngữ như `sang` hoặc `chuyển thành`.

