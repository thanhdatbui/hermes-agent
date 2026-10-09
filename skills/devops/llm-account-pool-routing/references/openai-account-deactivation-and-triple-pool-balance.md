# OpenAI Account Deactivation & Triple-Pool Balance Protocol

## 1. Dual-Cook on OpenAI Account Deactivation
Khi OpenAI vô hiệu hóa một tài khoản (do vi phạm TOS, cờ bot hoặc rà soát hàng loạt):
- **Bên ChatGPT-Web (Browser/GPM):** Khi submit email tại `chatgpt.com/auth/login`, OpenAI redirect về:
  `https://auth.openai.com/error?payload=eyJraW5kIjoiZXJyb3IiLCJjb2RlIjoiYWNjb3VudF9kZWFjdGl2YXRlZCIsIm1lc3NhZ2UiOiJZb3VyIGFjY291bnQgaGFzIGJlZW4gZGVhY3RpdmF0ZWQuIn0`
  Payload JSON giải mã: `{"kind": "account_deactivated", "message": "Your account has been deactivated."}` hoặc `{"kind": "AccountDeactivated"}`.
- **Bên Codex CLI (OAuth Developer endpoint):** Dù file `token` OAuth/refresh token còn lưu trong máy, khi OmniRoute gửi request upstream lên `/v1/responses`, OpenAI lập tức thu hồi và trả về HTTP 401:
  `[401]: Encountered invalidated oauth token for user, failing request`
- **KỶ LUẬT XỬ LÝ (INVARIANT):**
  - Tài khoản đã bị deactivate ở OpenAI là **CHẾT ĐỒNG THỜI Ở CẢ HAI BÊN**.
  - Khi phát hiện `AccountDeactivated` ở Web hoặc `invalidated oauth token` (401) ở Codex:
    1. Lập tức set `is_active = 0, test_status = 'banned'` trên **CẢ HAI provider** (`chatgpt-web` LẪN `codex`).
    2. Loại bỏ hoàn toàn `connectionId` của tài khoản này khỏi toàn bộ các combo (`codex-luna`, `codex-terra`, `gpt-web-sol`, `chatgpt-web-pool`).
    3. Tuyệt đối không để sót connection 401 trong pool vì sẽ làm delay request hoặc kích hoạt circuit breaker giả.

## 2. Triple-Pool Architecture & Cân Bằng Lực Lượng (27 - 27 - 27)
Hệ thống vận hành 3 pool song song trong OmniRoute (`:20129`), đồng bộ số lượng tài khoản LIVE 100%:
1. **`codex-luna` (27 accs):** Dành riêng cho **Worker T2 (`codex/gpt-5.6-luna-high`)**. Thi công code trong lồng O(1) <= 30 dòng. Timeout = 90000ms.
2. **`codex-terra` (27 accs):** Dành cho dự phòng / benchmark (`codex/gpt-5.6-terra`). Timeout = 90000ms.
3. **`gpt-web-sol` (27 accs):** Dành cho **Planner T2 & Reviewer Chốt Phiên (`chatgpt-web/gpt-5.6-sol-high`)**. 
   - Tiêu tốn 0đ quota Codex.
   - Thắng tuyệt đối 5/5 trận trong Benchmark Tournament đối đầu Terra Codex do Claude Code CLI thẩm định (85/100 vs 62/100).
   - Timeout = 120000ms.

## 3. Quy Tắc Điều Phối An Toàn Tránh Cờ Lạm Dụng OpenAI
- **Strategy:** Luôn cấu hình `strategy: "p2c"` (Power of Two Choices) kết hợp `disableSessionStickiness: true` và `disablePromptCacheAffinity: true`.
- **IP Isolation:** 100% tài khoản Web được gán proxy Mobi 4G 1-1 riêng biệt qua `proxy_assignments` (port 5105, 5113, 5125...).
- **Fallback OpenCode Bridge (`:20130`):** Timeout trong `opencode_bridge.py` bắt buộc đặt $\ge 90$s (120s nếu có ảnh). Không được đặt $\le 35$s tránh tự ngắt request khi model đang sinh câu trả lời.
