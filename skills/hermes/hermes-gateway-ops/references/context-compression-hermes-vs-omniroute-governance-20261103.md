# Triage & Quản Trị Cơ Chế Nén Context: Hermes vs OmniRoute (2026-11-03)

## 1. Phân Định Ranh Giới Kiến Trúc (SSOT: Hermes vs Proxy)
- **Nén ngữ cảnh BẮT BUỘC nằm ở Hermes (`agent/context_compressor.py`):**
  - Hermes là client nắm giữ transcript hội thoại, hiểu rõ cấu trúc session, phân biệt được system prompt, user intent và tool calls.
  - CẤM TUYỆT ĐỐI chế cháo logic nén/gọt tin nhắn vào tầng proxy OmniRoute (`open-sse/services/compression/lite.ts`). Việc này gây rủi ro đứt gãy schema (đặc biệt khi có payload đa phương thức / ảnh Base64) và dễ phá vỡ build frontend của OmniRoute.

## 2. Tử Huyệt Build Frontend OmniRoute (`build:backend` stub trap)
- Trong `scripts/build/backendOnlyPages.mjs`, cờ `OMNIROUTE_BUILD_BACKEND_ONLY=1` dùng cơ chế stub rỗng toàn bộ 126 trang App-Router của Next.js để build backend siêu tốc.
- Hậu quả: File bundle standalone sinh ra **chỉ có API backend, hoàn toàn không có frontend Dashboard**, dẫn đến việc mở web `:20128` / `:20129` bị lỗi 404, vỡ layout, trắng trang hoặc crash giao diện.
- **Quy tắc:** CẤM Coordinator táy máy sửa backend OmniRoute rồi chạy `build:backend` để thử nghiệm tính năng nén tự chế. Mọi thay đổi OmniRoute phải giữ nguyên trạng frontend hoặc chạy quy trình build full an toàn.

## 3. Lựa Chọn Model Nén Auxiliary (`auxiliary.compression.model`)
- **Nguy cơ của ChatGPT Web (`gpt-web-sol` / `gpt-5.6-luna`):** Context window đầu vào của ChatGPT Web bị giới hạn ở 32k - 64k tokens. Dù Hermes có truncation cap, nếu session có lịch sử turn dày, payload nén vẫn có nguy cơ vượt trần gây lỗi `400 / 413 Context Overflow`.
- **Lựa chọn an toàn tuyệt đối:** **`gemini-web` (Argon Gemini Web)**:
  - Cửa sổ ngữ cảnh 1.000.000 tokens (1M).
  - Tốc độ sinh tóm tắt 6-9s cho payload 30k-100k tokens.
  - Cấu hình chuẩn:
    ```yaml
    auxiliary:
      compression:
        provider: omni
        model: gemini-web
        timeout: 300
    ```

## 4. Tối Ưu "Nén Khôn Cơ Học" Trong Hermes (`context_compressor.py`)
- **Tầng 1 - Mechanical Tool Pruning:**
  - Tại Phase 1 của `compress()`, sau khi `_prune_old_tool_results()` gọt các tool output cũ thành 1 dòng (`[terminal] ran cmd -> exit 0`), kiểm tra:
    ```python
    if estimate_messages_tokens_rough(messages) < self.threshold_tokens:
        logger.info("Mechanical pruning brought tokens below threshold; skipping LLM summarizer to keep prompt cache.")
        return messages
    ```
  - Nếu dung lượng giảm dưới ngưỡng, bỏ qua hoàn toàn việc gọi LLM tóm tắt $\to$ Giữ nguyên vẹn 100% Prompt Cache cho Google Gemini, turn sau phản hồi tức thì mà không bị lag.
- **Tầng 2 - Serialization Cap Bảo Vệ Upstream:**
  - `_CONTENT_MAX = 6000` chars/message, `_CONTENT_HEAD = 4000`, `_CONTENT_TAIL = 1500`, `_TOOL_ARGS_MAX = 1500`.
  - Dù tổng session đạt 600k tokens, payload thực tế gửi sang `gemini-web` chỉ rơi vào 30k - 60k tokens, nằm hoàn toàn trong vùng xử lý tối ưu của model.
