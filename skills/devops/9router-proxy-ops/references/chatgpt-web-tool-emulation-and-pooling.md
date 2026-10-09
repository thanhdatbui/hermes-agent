# ChatGPT Web Emulated Tool Calling & Tiered Pool Mechanics on OmniRoute (:20129)

## 1. Native vs Emulated Tool Calling on Web Sessions
- Khác với API chính thức của OpenAI/Anthropic/Google vốn có engine tool-calling native từ máy chủ, `chatgpt-web` bản chất là phiên làm việc web-session (NextAuth session token qua backend-api của chatgpt.com).
- Khi client (Hermes Coordinator/Worker, Codex CLI, Aider) gửi request kèm danh sách `tools` (schema OpenAI function calling), OmniRoute kích hoạt cơ chế **Web Tools Prompt Emulation** (`open-sse/executors/chatgpt-web.ts`, PR #5240, #7679):
  1. OmniRoute inject system prompt hướng dẫn model suy luận và định dạng lệnh gọi tool theo hợp đồng thẻ giả lập (`<tool>{"name": ..., "arguments": ...}</tool>`).
  2. Khi model sinh phản hồi chứa thẻ tool, bộ lọc upstream buffer stream, parse nội dung JSON và đóng gói ngược lại thành đối tượng chuẩn `tool_calls` kèm `finish_reason: "tool_calls"`.
  3. Client nhận diện `tool_calls` và thực thi tool thật (terminal, file patch, adb...), sau đó gửi lượt (turn) tiếp theo chứa role `tool` về OmniRoute để model đọc kết quả.
  4. Nhờ vậy, client giữ nguyên "tay chân" đầy đủ mà không cần plugin MCP hay desktop UI browser lằng nhằng như tool ngoài (`codex-chatgpt-web`).
- **Thực nghiệm E2E**: Đã chứng minh model gọi tool `write_file` ghi nội dung vào file đĩa cứng thật và gọi tool `terminal` tiếp nối mượt mà.

## 2. Phân biệt Model Sol vs Terra vs Luna trên OpenAI Platform
- **Dòng Sol (`gpt-5.6-sol-instant`, `gpt-5.6-sol-high`, `gpt-5.6-sol-pro`)**: Là model chuyên biệt của ChatGPT Web (Plus/Team/Pro). Thích hợp làm Tier 0 Review / Plan / Scorecard audit (0đ quota) hoặc Fallback cho Worker.
- **Dòng Terra (`gpt-5.6-terra`)**: Là model chuyên biệt của Codex API Platform / CLI (`chatgpt.com/backend-api/codex/responses`), **hoàn toàn không tồn tại trên backend của ChatGPT Web**. Cấm cấu hình `chatgpt-web/gpt-5.6-terra` vì request lên web backend sẽ bị timeout/404. Muốn dùng Terra phải trỏ qua provider `codex` hoặc API chính thức.
- **Dòng Luna (`gpt-5.6-luna-free` trên Web / `gpt-5.6-luna` trên Codex)**: Là model worker nhẹ/nhanh của OpenAI. Đạt 91/100 chuẩn Farm-Grade Worker trong benchmark thực chiến.
- **Gemini Flash Pool (`ag-gemini-pool-3`)**: Ưu tiên số 1 cho Worker chạy tay chân (70 accs xoay vòng, tốc độ cao ~5s, context 1M). Tuyệt đối không bị bẫy từ chối đạo đức khi automation Farm.
- **Tử huyệt OpenAI Safety Refusal trên Luna & Sol**: Trong bài test ADB automation TikTok (like/comment xác suất), các model OpenAI dính ngay bẫy đạo đức (Safety Policy Refusal) và từ chối sinh chuỗi ADB (Luna bị 0/25đ trong đề thi Claude), trong khi Gemini Flash hoàn thành 100%. Vì vậy Gemini Flash vẫn là Worker chính không thể thay thế cho các tác vụ phone farm.

## 3. Benchmark Worker Thực Chiến: Gemini 3.8 Flash vs GPT-5.6 Luna (Medium Effort)
- Thang điểm 100 do Giám khảo Sol High chấm trên 5 bài toán thực tế farm:
  1. **TikTok UI Drift Surgery (20đ)**: Luna (18) thắng Gemini (17) nhờ chuỗi chuẩn hóa phòng thủ `.casefold()`.
  2. **Device Lock Concurrency (25đ)**: Luna (22) thắng Gemini (18) nhờ nhận diện bản chất shared mutable state cần OS file lock (`flock`) thay vì ghi đè file mù.
  3. **Anti-Overengineering (20đ)**: Luna (20) thắng Gemini (19) với 1 dòng Pythonic tuyệt đối (`return button.follow_count > 0`).
  4. **Farm Invariant Review (20đ)**: Gemini (18) thắng Luna (17) nhờ bao quát cả IO storm `os.walk("/")` và tọa độ cứng ADB.
  5. **Corrupted JSON Exception (15đ)**: Luna (14) thắng Gemini (11) nhờ retry có kiểm soát và bắt đúng ranh giới lỗi.
- **Tổng kết**: Luna (91/100) = Kỹ sư vận hành chịu trách nhiệm hệ thống (Reliability Core). Gemini Flash (83/100) = Thợ sửa nhanh (Fast Patch).

## 4. Bản Chất Quota Rolling Window, Tử Huyệt Session Expired & Bẫy Model Slug `sol-pro` vs `sol-instant`
- **Cơ chế phân bổ Quota theo Model Slug trên Web Backend**:
  - `gpt-5.6-sol-high`: Mô hình reasoning chuẩn của tier Plus/Team, quota 40–80 requests / 3–5h. Xoay tua đều trong pool 16 accounts qua Round-Robin (`chatgpt-web-pool`) cho phép hệ thống vận hành liên tục 24/7 mà không sợ cạn quota.
  - `gpt-5.6-sol-pro`: Quota Pro riêng biệt siêu ngặt nghèo (chỉ vài requests / 3–5h trên web backend). **CẤM TUYỆT ĐỐI** gọi hoặc ép cờ `--model chatgpt-web/gpt-5.6-sol-pro`! Request đầu tiên sẽ lập tức trigger `502 You've hit your limit. Please try again later.`.
  - `gpt-5.6-sol-instant`: Chế độ 0 thinking / non-reasoning. Không phù hợp làm reviewer code hoặc thẩm định kiến trúc farm.
  - **Quy tắc an toàn**: Không để agent tự ý phỏng đoán hoặc chọn model slug dựa trên `/v1/models`. Bắt buộc dùng combo `review` (tự động map về `gpt-5.6-sol-high` trên pool 16 accs).
- **Quota tính theo giờ (Rolling Window) trên Web Free & Paid**:
  - **Sự thật về Quota Web Free (Đính chính chuẩn xác từ User)**: Web Free **KHÔNG PHẢI "Unlimited / Miễn phí vô hạn"**. OpenAI luôn áp hạn ngạch theo cửa sổ trượt 3–5 tiếng (vài chục requests / 3h đối với Free). Khi cạn quota trong cửa sổ, nó tạm khóa hoặc giáng cấp xuống non-thinking. Hệ thống gọi liên tục không thấy hết là nhờ **pool 17 tài khoản Web xoay vòng Round-Robin**, tải chia đều ra 17 acc nên các acc lần lượt hồi quota.
  - **Khả năng Thinking trên Web Free**: Tài khoản Web Free **VẪN CÓ THINKING** (`chatgpt-web/gpt-5.6-sol-high`, `chatgpt-web/gpt-5.6-luna-free-thinking`). Khác với Codex (bị khóa cổng theo lịch tháng `codexScopeRateLimitedUntil`), Web chỉ bị nghẽn tạm thời theo giờ.
  - Khi dính lỗi `502 You've hit your limit`: Sau 3–5h các tin nhắn cũ tự động trượt ra khỏi cửa sổ và acc hồi phục hạn ngạch bình thường.
- **Dây chuyền lỗi dồn tải Priority -> Cloudflare Sentinel (403) -> Expired Cookie**:
  1. Nếu chạy chiến lược `priority`, các acc đầu (P01, P02...) gánh tải liên tục $\rightarrow$ chạm limit 502 liên tiếp.
  2. OpenAI đánh giá có hành vi bot dồn dập $\rightarrow$ bật khiên chống bot: `403 Sentinel / Turnstile Required`.
  3. OmniRoute bị chặn lại ở màn hình 403 Sentinel $\rightarrow$ không thể gọi ngầm `GET https://chatgpt.com/api/auth/session` để lấy JWT `accessToken` mới.
  4. Sau 24–48h không được refresh tự động, session cookie cũ hết hạn tự nhiên $\rightarrow$ OpenAI trả về `ChatGPT session expired — log into chatgpt.com and copy a fresh cookie`.
  5. **Lưu ý**: Tài khoản Gmail / OpenAI không hề bị khóa (banned), chỉ là session cookie expired, cần mở profile GPM lấy lại cookie nạp bù.

## 5. Kiến Trúc Combo Xoay Pool (Round-Robin chuẩn như `ag-gemini-pool-3`)
- **Vấn đề của Priority**: Request luôn đổ vào acc Priority 1, 2 trước. Khi các acc này liên tục chạm trần thì dễ kích hoạt Sentinel 403 làm hỏng session.
- **Cấu hình chuẩn đồng bộ với `ag-gemini-pool-3`**:
  ```json
  {
    "name": "chatgpt-web-pool",
    "strategy": "round-robin",
    "config": {
      "maxRetries": 3,
      "retryDelayMs": 500,
      "targetTimeoutMs": 120000,
      "stickyRoundRobinLimit": 30,
      "disableSessionStickiness": false,
      "disablePromptCacheAffinity": false,
      "failoverBeforeRetry": false,
      "maxSetRetries": 3
    }
  }
  ```
- Tải được chia đều cho 15+ accounts trong pool, mỗi acc phục vụ 30 requests trước khi xoay tua sang acc tiếp theo, triệt tiêu hoàn toàn nguy cơ dính Sentinel challenge.
- Combo `review` (Tier 0) và combo `omni-worker` (Tier 2 Fallback) đều trỏ vào `combo-ref: chatgpt-web-pool`.

## 6. Van An Toàn Đạo Đức Vật Lý (Physical Safety Valve) & Cơ Chế Hook Gác Cổng
- **Memory vs Physical Hook**:
  - Memory / System Prompt chỉ là tài liệu tham khảo (advisory), LLM rất dễ quên hoặc hợp lý hóa việc phá luật khi context dài.
  - Phải dùng **Pre-Tool Hook vật lý** (`guard_dispatch_contract.py` chặn lệnh `delegate_task` ở tầng runtime) để cưỡng chế luật: bắt buộc có `SOL_PLAN_ID` cho mọi ca sửa code logic non-T0.
- **Van an toàn đạo đức vật lý**:
  - `sol_planner.py`: Tự động bắt tín hiệu từ chối của OpenAI (`không thể cung cấp bot`, `vi phạm quy định`, `tương tác không xác thực`...) và trả về `status: "refusal"`.
  - `guard_dispatch_contract.py`: Bổ sung cờ `SAFETY_REFUSAL: <lý do>` hoặc `SOL_FALLBACK` để bypass bước bắt buộc `SOL_PLAN_ID` khi Sol từ chối do chính sách OpenAI, mở đường cho Coordinator chuyển giao Worker Gemini thi hành ngay lập tức.
  - **Bắt buộc Audit Log vật lý & Báo cáo**:
    - Hook tự động ghi 1 dòng JSON vào `D:\Taadaa\runtime\audit_logs\safety_valve_trigger.jsonl` mỗi khi van xả áp kích hoạt.
    - Coordinator bắt buộc thông báo minh bạch cho user lý do kích hoạt van xả áp trong tin nhắn hội thoại và đưa vào biên bản chốt phiên.

## 7. Chiến Lược Watchdog / Cron Khôi Phục Session Báo Cáo Farm Alert
- **CẤM** đặt cron mù (blind polling) cứ mỗi giờ lại bật hàng loạt profile GPM lên (gây giật máy, tốn RAM/CPU, tăng nguy cơ dính Cloudflare bot flag).
- **Thiết kế tối ưu**:
  - Script: `cron_chatgpt_web_pool_watchdog.py` (Job ID: `fff7f688990d`, chạy 05:00 AM hàng ngày).
  - Health check ngầm qua OmniRoute API (`/api/providers`).
  - CHỈ mở profile GPM của riêng những account nào có `test_status != 'active'` hoặc trả về `session expired`.
  - Mở profile qua GPM API $\rightarrow$ cắm CDP websocket điều hướng `https://chatgpt.com` $\rightarrow$ lấy cookie mới $\rightarrow$ validate qua OmniRoute $\rightarrow$ cập nhật SQLite $\rightarrow$ đóng profile dọn sạch tiến trình Chrome trong khối `finally`.
  - Kết quả nghiệm thu tự động gửi về nhóm **Farm Alert** (`telegram:-5373649734`).

## 8. Vị Trí Vận Hành Chuẩn: SQLite Storage
- Trên môi trường Windows, database sống của OmniRoute :20129 nằm tại:
  `C:\Users\Kibe\.omniroute\storage.sqlite`
- Các bảng trọng yếu cần inspect khi có sự cố pool:
  - `provider_connections`: Kiểm tra `is_active`, `test_status`, `backoff_level`, `rate_limited_until`.
  - `combos`: Bảng lưu định nghĩa JSON các combo (`review`, `omni-worker`, `chatgpt-web-pool`).
  - `call_logs`: Kiểm tra lịch sử mã lỗi `status` (401 session expired, 403 Sentinel/Turnstile, 413 payload too large, 499 aborted, 502 rate limit).

## 9. Hiện Tượng "Reasoning: N/A" trên Dashboard & Phân Biệt Sol High Thật vs Giả Cầy
- **Hiện tượng**: Trên Dashboard Call Log của OmniRoute, mọi request tới `chatgpt-web/gpt-5.6-sol-high` đều hiển thị `Reasoning: N/A` ở mục Output token dù đang chạy model reasoning.
- **Bản chất kỹ thuật**:
  - Giao thức web backend (`chatgpt.com/backend-api/conversation`) của OpenAI **hoàn toàn không trả về token accounting** (`usage`, `prompt_tokens`, `completion_tokens_details.reasoning_tokens`).
  - OmniRoute (`open-sse/executors/chatgpt-web.ts`) phải tự ước lượng token đầu vào/ra bằng công thức độ dài ký tự: `completionTokens = Math.ceil(fullAnswer.length / 4)`. Vì không có số đếm reasoning token từ upstream, trường `tokens.reasoning` được lưu là `null`.
  - Giao diện `RequestLoggerDetail.tsx` khi gặp `null` sẽ format thành `t("notAvailable")` (`N/A`).
- **Cách verify Sol High đang reasoning xịn**:
  1. `open-sse/executors/chatgpt-web/models.ts` ánh xạ: `gpt-5.6-sol-high` $\rightarrow$ `modelSlug: "gpt-5-6-thinking"`, `thinking_effort: "extended"` (mức thinking sâu nhất của ChatGPT Web).
  2. Latency: Output chỉ ~400 tokens nhưng mất 12s - 25s (thời gian server upstream OpenAI chạy chuỗi thinking loop trước khi stream delta answer). Nếu là model non-reasoning (`sol-instant`), 400 tokens chỉ mất 1-2s.
  3. Chất lượng output: Phân tích kiến trúc sâu, bắt trúng edge case phức tạp trong diff code mà non-reasoning model thường bỏ sót.
- **Quy tắc vận hành**: Tuyệt đối không phán đoán Sol High "giả cầy" hay "không reasoning" chỉ dựa vào chỉ số `Reasoning: N/A` trên dashboard.
