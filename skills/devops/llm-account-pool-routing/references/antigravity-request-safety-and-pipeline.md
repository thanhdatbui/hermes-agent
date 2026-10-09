# Antigravity Request Safety & Upstream Pipeline Architecture

## 1. Context & Upstream Endpoint
OmniRoute translates standard OpenAI/Claude API requests into Google Antigravity (Cloud Code) internal format (`/v1internal:streamGenerateContent` or similar) via `open-sse/translator/request/openai-to-gemini.ts` and `open-sse/executors/antigravity.ts`.

To prevent account suspensions, 400 bad requests, and 429 resource exhausted errors, the request pipeline enforces strict safety normalization:

---

## 2. Core Safety Normalization Rules

### A. System Instruction vs Client System Prompt Relocation (#9030)
- **Problem:** Google Cloud Code / Antigravity internal backend expects only the official Antigravity IDE signature prompt in `systemInstruction`. If large agent prompts (e.g. Hermes coordinator rules, skills, memories, 50k-125k tokens) are placed in `systemInstruction`, Google backend rejects the request with `429 RESOURCE_EXHAUSTED` or `400 INVALID_ARGUMENT`.
- **Solution:** 
  - `systemInstruction` is strictly populated ONLY with the canonical:
    ```text
    You are Antigravity, a powerful agentic AI coding assistant designed by the Google Deepmind team working on Advanced Agentic Coding.
    You are pair programming with a USER to solve their coding task. The task may require creating a new codebase, modifying or debugging an existing codebase, or simply answering a question.
    **Absolute paths only**
    **Proactiveness**
    ```
  - Any client-provided system prompt is prepended into `contents[0]` (the first user message).

---

### B. Tool Name Collision Filtering
- **Problem:** Antigravity backend rejects requests with `400 Bad Request` if custom `functionDeclarations` include tool names that collide with Google built-in tools.
- **Solution:** OmniRoute filters out the following names from `functionDeclarations`:
  - `google_search`
  - `web_search`
  - `search_web`
  - `googleSearch`

---

### C. Safety Categories Normalization
- **Harm Categories Set to `OFF`:**
  - `HARM_CATEGORY_HATE_SPEECH`: `OFF`
  - `HARM_CATEGORY_DANGEROUS_CONTENT`: `OFF`
  - `HARM_CATEGORY_SEXUALLY_EXPLICIT`: `OFF`
  - `HARM_CATEGORY_HARASSMENT`: `OFF`
- **Unsupported Categories Stripped:**
  - `HARM_CATEGORY_CIVIC_INTEGRITY` must NOT be sent to Antigravity endpoints (causes `400 Bad Request`).

---

### D. Client Fingerprinting & Request Envelope
- **User-Agent:** Pinned to darwin/arm64 macOS IDE build:
  - `antigravity/ide/<version> darwin/arm64`
  - `X-Goog-Api-Client: gl-node/22.21.1`
- **Request Envelope:**
  ```json
  {
    "project": "<discovered-cloud-code-project-id>",
    "userAgent": "antigravity",
    "requestType": "agent",
    "requestId": "<uuid>",
    "request": {
      "contents": [...],
      "systemInstruction": { "role": "system", "parts": [{ "text": "..." }] },
      "generationConfig": { ... },
      "safetySettings": [ ... ]
    }
  }
  ```

---

### E. Flash vs Pro Thinking / Reasoning Behavior (Opaque vs Verbose)
- **Problem / Symptom:** Khi gọi `gemini-3.8-flash-tiered` hoặc `gemini-3.7-flash-tiered` qua OmniRoute (:20129) / Antigravity, response hoàn toàn không có `reasoning_content` (hay chunk suy nghĩ), dù trong call logs OmniRoute vẫn ghi nhận `tokens.reasoning` (khoảng vài chục đến hàng trăm token) với `reasoning_source: 'usage'`.
- **Upstream Root Cause:**
  - Google Cloud Code backend nội bộ (`/v1internal:streamGenerateContent`) áp dụng cơ chế **silent / opaque reasoning** đối với các model Flash (`gemini-3.8-flash-tiered`, `gemini-3.7-flash-tiered`).
  - Google upstream vẫn thực thi thinking nội bộ (dựa theo `thinkingBudget` trong `generationConfig.thinkingConfig`), đo lường token suy nghĩ (`thoughtsTokenCount` trong `usageMetadata`), và trả về `thoughtSignature` mã hóa (để xác thực tool call).
  - TUY NHIÊN, Google **hoàn toàn không stream bất kỳ part văn bản nào có cờ `thought: true`** đối với model Flash.
  - Do upstream không trả về text thought, translator `gemini-to-openai.ts` của OmniRoute không có dữ liệu để map vào `delta.reasoning_content` hay `message.reasoning_content`.
  - Ngược lại, model Pro (`antigravity/gemini-3.1-pro-high` / `gemini-pro-default`) được Google upstream stream đầy đủ các chunk `{ thought: true, text: "..." }` và OmniRoute chuyển thành `reasoning_content` bình thường.
- **Operational Rule:**
  - `gemini-3.8-flash-tiered` VẪN suy nghĩ và giải quyết bài toán logic đúng, chỉ là Google không xuất text suy nghĩ ra ngoài.
  - TUYỆT ĐỐI KHÔNG sửa translator hay chế thêm wrapper ép model Flash nhả thought text.
  - Nếu workflow/agent yêu cầu bắt buộc phải đọc/hiển thị `reasoning_content`, phải route sang `antigravity/gemini-3.1-pro-high` hoặc các model Claude thinking (`antigravity/claude-sonnet-4-6-high`, `claude-opus-4-6-thinking`).

---

### F. Model ID Naming: `3.7-flash-high` vs `3.8-flash-tiered` & OmniRoute UI Reasoning Badge
- **User Confusion / Phenomenon:** Người dùng thắc mắc tại sao trước đây gọi Gemini 3.7 thì OmniRoute báo log là `gemini-3.7-flash-high` và có reasoning, nhưng chuyển sang Gemini 3.8 thì OmniRoute báo log là `gemini-3.8-flash-tiered` và nghi ngờ 3.8 không có reasoning.
- **Root Cause & Ground-Truth Analysis:**
  1. **OmniRoute UI Reasoning Badge:** 
     - Trên giao diện OmniRoute (`/dashboard/logs`), badge tím `Reasoning: X` và log terminal `R=X` được lấy từ trường số lượng token `tokens.reasoning` (từ `usageMetadata.thoughtsTokenCount` của Google), KHÔNG PHẢI từ text nội suy trong phản hồi.
     - Cả `gemini-3.7-flash-high` (53,472 cuộc gọi trong DB) và `gemini-3.8-flash-tiered` (5,920 cuộc gọi trong DB) đều có tỷ lệ ghi nhận reasoning tokens tương đương (~91.6% - 91.9%) với `reasoning_source: 'usage'`. Cả hai model đều có **CHÍNH XÁC 0 lượt trả text reasoning thô** (`reasoning_content: null`).
  2. **Tên gọi Model (`-high` vs `-tiered`):**
     - Phía Google Antigravity backend thực tế chỉ có ID gốc kết thúc bằng `-tiered` (`gemini-3.7-flash-tiered` và `gemini-3.8-flash-tiered`).
     - OmniRoute v3.8.50 có sẵn static alias và spec cho 3.7: `"gemini-3.7-flash-high": "gemini-3.7-flash-tiered"` (kèm preset thinking budget 24576). Khi client gọi `3.7-flash-high`, OmniRoute ghi nhận log theo alias đã gọi.
     - Đối với 3.8, do mới ra mắt nên OmniRoute chưa có alias built-in. Khi auto-import từ Google `:fetchAvailableModels`, OmniRoute lưu đúng tên ID kỹ thuật gốc `gemini-3.8-flash-tiered`. Nếu gọi `gemini-3.8-flash-high` mà chưa có alias, OmniRoute chuyển nguyên chuỗi sang Google dẫn tới lỗi HTTP 403 / 429.
  3. **Cách bật alias `-high` cho 3.8 an toàn (không cần build code):**
     - Cập nhật bản ghi `mitmAlias` trong bảng `key_value` của SQLite `storage.sqlite` (namespace `mitmAlias`, key `antigravity`):
       Thêm cặp `"gemini-3.8-flash-high": "antigravity/gemini-3.8-flash-tiered"`.
     - Khi đó, các pool/client có thể gọi tên `antigravity/gemini-3.8-flash-high`, OmniRoute sẽ tự map về `gemini-3.8-flash-tiered` upstream và hiển thị log đẹp mắt như 3.7.

