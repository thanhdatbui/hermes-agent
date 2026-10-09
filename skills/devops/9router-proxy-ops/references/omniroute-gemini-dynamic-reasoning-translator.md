# OmniRoute Gemini Dynamic / Tiered Reasoning Translator Architecture

## 1. Hiện trạng & Vấn đề Static Allocation
- **Kiến trúc Upstream (Google Antigravity / Gemini 3.7 & 3.8 Flash):**
  - Dòng Flash Tiered (`gemini-3.7-flash-tiered`, `gemini-3.8-flash-tiered`) hỗ trợ cơ chế **Dynamic Reasoning**: tự co giãn số lượng token suy nghĩ dựa vào độ khó của prompt (câu hỏi dễ tốn 100–300 token, câu hỏi khó tự đào sâu).
- **Vấn đề trong OmniRoute (`open-sse/translator/request/openai-to-gemini.ts`):**
  1. Khi client gửi `reasoning_effort: "auto"`: OmniRoute map `"auto"` về `highBudget` (24.576 / 32.768 tokens), biến dynamic intent thành fixed high budget.
  2. Khi client bỏ trống không truyền tham số reasoning: `openai-to-gemini.ts` fallback đọc `defaultThinkingBudget` từ `modelSpecs.ts` (gán cứng 8.192 tokens cho bản 3.8).
  3. Hậu quả: 100% request qua OmniRoute đều gửi một con số cụ thể trong `generationConfig.thinkingConfig.thinkingBudget`, tước quyền tự co giãn của model.

## 2. Thẩm định kiến trúc từ Sol Web (GPT-5.6 Sol) & Antigravity Upstream
- **Cạm bẫy với `thinkingBudget: -1`:**
  - Google Gemini API trên một số backend (như Cloud Code / Antigravity) validate schema `thinkingBudget` là số nguyên không âm (`>= 0`).
  - Gửi `-1` có nguy cơ văng `400 INVALID_ARGUMENT: thinkingBudget must be >= 0`.
- **Giải pháp chuẩn xác và an toàn nhất:**
  - **Omit `thinkingBudget` hoàn toàn** khi `reasoning_effort === "auto"` (hoặc model `-tiered` không chỉ định budget).
  - Chỉ gửi:
    ```json
    "generationConfig": {
      "thinkingConfig": {
        "includeThoughts": true
      }
    }
    ```
  - Khi payload không chứa key `thinkingBudget`, Google Antigravity backend tự động kích hoạt chế độ suy luận Dynamic / Adaptive, số lượng token suy nghĩ được ghi nhận và đo lường đầy đủ qua `usageMetadata.thoughtsTokenCount`.

## 3. Tác động tới Tool-Calling, Latency & Streaming
- **Tool Calling:** Hoàn toàn độc lập với format của `functionDeclarations` / tool schema; không gây vỡ payload gọi tool.
- **Streaming SSE:** Giao thức SSE không đổi, nhưng thời gian nhận token đầu tiên (Time To First Token - TTFT) sẽ biến thiên linh hoạt theo độ phức tạp của bài toán thay vì cố định như khi ép budget cao.
