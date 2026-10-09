# Cockpit (:60818) vs OmniRoute (:20129) vs 9Router (:20128) - Codex Model & OAuth Archeology

## 1. Bản đồ Thế hệ Model Codex (Thực tế Binary & Upstream)
- **Thế hệ GPT-6**:
  - `gpt-6-luna`: Lightweight / Fast tier. Acc Free chạy **200 OK**, latency ~8-22s, rất nhẹ quota (~0.1-0.5%).
  - `gpt-6-sol` / `gpt-6-astra`: Flagship & High-reasoning tier. Upstream OpenAI hard-block token OAuth của acc Free (`HTTP 400: The 'gpt-6-sol' model is not supported when using Codex with a ChatGPT account`). Yêu cầu acc trả phí (Plus/Team/Pro).
- **Thế hệ GPT-5.6**:
  - `gpt-5.6-luna`: Chạy 200 OK trên acc Free (35.7k+ calls trong log, 91.8% success).
  - `gpt-5.6-terra`: Chạy 200 OK trên acc Free (5k+ calls, reasoning sâu ~353 tokens, latency cao 30-45s, dễ timeout nếu context >80k).
  - `gpt-5.6-sol`: Hard-block trên acc Free.
- **Thế hệ GPT-5.5 / Review**:
  - `gpt-5.5`, `codex-auto-review`: 200 OK trên acc Free.
- **Lưu ý định danh**: Không có model nào tên là `sol 6.1` hay `gpt-6.1`. "6.1 Sol" là tên do user/cộng đồng tự đặt alias.

## 2. Trạng thái hỗ trợ trên 3 Gateway
1. **Cockpit Proxy (`:60818`)**:
   - Nhân `cockpit-cliproxy.exe` đã cập nhật đầy đủ catalog thế hệ GPT-6 (`gpt-6-luna`, `gpt-6-sol`, `gpt-6-astra`).
   - Kết nối trực tiếp dàn account ChatGPT Free (Hotmail OAuth) vào upstream OpenAI Codex.
2. **OmniRoute (`:20129`)**:
   - Code `open-sse/config/providers/registry/codex/index.ts` chỉ mới có catalog thế hệ 5.6 (`gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`, `gpt-5.5`).
   - Chưa cập nhật định nghĩa `gpt-6-luna` vào provider `codex`.
3. **9Router (`:20128`)**:
   - DB `providerConnections` chưa add connection nào thuộc provider `codex`.
   - Các model mang tên `gpt-5.6-luna` trên 9Router hiện tại là alias ảo trỏ về Gemini Flash Tiered (Google Antigravity pool).

## 3. Quy tắc vận hành & Khắc phục
- Muốn dùng `gpt-6-luna` xịn nhất từ dàn acc Free: Gọi trực tiếp vào Cockpit (`http://127.0.0.1:60818/v1`) hoặc cấu hình Cockpit làm Custom OpenAI Provider trên 9Router/OmniRoute.
- Tránh nhầm lẫn OpenRouter (cloud aggregator tính phí) với provider `codex` nội bộ.
