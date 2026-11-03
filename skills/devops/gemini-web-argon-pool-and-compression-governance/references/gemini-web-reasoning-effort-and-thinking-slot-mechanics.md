# Gemini Web Reasoning & Thinking Slot Mechanism (:20129)

## 1. Bản Chất Điều Khiển Thinking Trên Gemini-Web (OmniRoute)
* Khác với các mô hình Cloud API truyền thống (dùng `thinking: { budget_tokens: ... }`), `gemini-web` trên OmniRoute giao tiếp qua reverse-engineered endpoint `StreamGenerate` (Protobuf array 80 slots).
* File mã nguồn: `open-sse/executors/gemini-web.ts`:
  ```typescript
  function resolveThinkingSlot(reasoningEffort?: string | null): unknown {
    switch (reasoningEffort?.trim().toLowerCase()) {
      case "high":   return [[0]];   // Kích hoạt Maximum Thinking Slot
      case "low":    return [[4]];
      case "none":   return null;
      default:       return [[2]];   // Default thinking slot
    }
  }
  // Gắn trực tiếp vào Slot 17 của protobuf payload gửi Google:
  inner[17] = resolveThinkingSlot(reasoningEffort);
  ```

## 2. Capability Guard & Quy Chuẩn Gửi Request
* Kiểm tra tại `open-sse/executors/gemini-web/capabilities.ts`:
  * Cho phép các mức `reasoning_effort`: `["none", "minimal", "low", "medium", "high", "default"]`.
  * Yêu cầu gửi tham số `"reasoning_effort": "high"` ở root JSON body của request `/v1/chat/completions`.
* **Cạm bẫy:**
  * Nếu client (như `gate_b_planner.py` hoặc `consult_advisor.py`) chỉ gửi `{"model": "...", "messages": [...]}` mà quên tham số `reasoning_effort`, request chỉ chạy ở mức thinking mặc định.
  * Khi cần giải thuật, lập plan O(1) hoặc tư vấn kiến trúc phức tạp, BẮT BUỘC chèn `"reasoning_effort": "high"`.

## 3. Kiến Trúc 20 Tài Khoản Đồng Bộ
* Hai combo `gemini-web` và `gemini-web-argon-pool` trong CSDL `storage.sqlite` bản chất trỏ chung vào cùng một tập tài khoản Google AI Pro (20 acc).
* Cả 2 combo phải luôn được đảm bảo đồng bộ trọn vẹn 20 accounts với strategy `cache-optimized` để tản đều tải qua hệ thống proxy 4G.
