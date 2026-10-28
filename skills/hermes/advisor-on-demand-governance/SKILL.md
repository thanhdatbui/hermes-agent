---
name: advisor-on-demand-governance
description: Use when configuring Advisor Sol. Enforces on-demand only.
---

# Advisor On-Demand Governance

## Core Principle
- **100% STRICTLY ON-DEMAND**: Never guess user intent. Never auto-append Advisor (Sol) responses to chat messages based on heuristic words (e.g., "tư vấn", "lời khuyên", "có nên", "theo mày", "đánh giá", "phân tích giúp") or sentence endings with question marks `?`.
- The user must explicitly summon Advisor Sol by name.
- **CẤM LỌC TỪNG TỪ (ERADICATE HEURISTIC GATES, DO NOT CHERRY-PICK WORDS)**: Tuyệt đối không tiếp cận theo hướng "xóa từng từ nghi vấn". Tiếng Việt đa dạng, xóa từ này thì câu hỏi kỹ thuật thông thường (ví dụ: *"canary xem cron có fix đc k ?"*) vẫn bị dính do dấu hỏi `?` hoặc cấu trúc nghi vấn. BẮT BUỘC xóa sạch 100% nhánh suy đoán cảm tính trong `_is_advice_request()` và `classify_advice_intent()`, chuyển thành công tắc so khớp cơ học: Chỉ kích hoạt khi chứa đích danh các từ khóa triệu hồi.

## Strict Triggers Allowlist
In `agent/conversation_loop.py` and `consult_advisor.py`, `_is_advice_request()` / `classify_advice_intent()` MUST only return `True` for explicit trigger phrases:
```python
_ADVISOR_EXPLICIT_TRIGGERS = (
    "gọi advisor",
    "hỏi sol",
    "gọi sol",
    "sol thấy sao",
    "nhờ sol review",
    "sol lên plan",
)
```

## Anti-Pattern / Pitfalls
- **Post-Turn Dual-Answer Leak (`consult_advisor.py`) & The Bare-Word "advisor" Trap**:
  * Even when conversation loop has advisor disabled, post-turn checks invoke `consult_advisor.py:ensure_dual_answer()`.
  * **The Bare-Word Trap (Trúng Bẫy Từ Khóa Đơn Lẻ)**: Nếu `explicit_patterns` chứa mẫu đơn lẻ như `r"\b(advisor|sol review)\b"`, bất kỳ tin nhắn nào của Operator chứa từ "advisor" (kể cả phàn nàn "cấm gọi advisor", "đừng spam advisor", "tắt advisor đi", "r t fix vụ spam advisor r sao session này vẫn cứ lải nhải v") sẽ vô tình kích hoạt `classify_advice_intent() == True`! Hậu quả: Hook ngầm âm thầm gọi Sol và nối đuôi `--- Advisor (Sol / review) ---` ngay vào đít tin nhắn phàn nàn của User!
  * **Quy Chuẩn Chặn Đứng Bắt Buộc**:
    1. **Strict Multi-Word Summoning**: BẮT BUỘC dùng `SUMMON_PATTERNS` với động từ triệu hồi rõ ràng (`gọi sol`, `hỏi sol`, `nhờ sol review`, `gọi advisor`, `hỏi advisor`, `sol lên plan`). Tuyệt đối CẤM regex chứa từ `advisor` hay `sol` đứng một mình.
    2. **Negation & Complaint Exclude Patterns**: BẮT BUỘC kiểm tra `EXCLUDE_PATTERNS` trước tiên: nếu câu chứa các từ khóa cấm/phàn nàn (`tắt`, `dừng`, `cấm`, `đừng`, `không`, `chớ`, `spam`, `lải nhải`, `nhảm`) đi kèm `advisor/sol` $\to$ Lập tức trả về `False` 100%, chặn đứng hoàn toàn việc auto-append ngoài ý muốn.
- **Heuristic Pattern Trap**: Do NOT match generic question markers like `has_phrase("nên") and "?" in text`. That causes normal coordinator inquiries (e.g. "canary xem cron có fix đc k ?") to trigger Advisor Sol unexpectedly, causing latency and frustrating the operator.
- **Stale Session & Gateway Daemon In-Memory Staleness (Bẫy Gateway Chưa Restart)**:
  * Khi deploy bản vá cơ học cho `consult_advisor.py` (như commit `d3d2e55` / `5d3f7f6` khóa chặt On-Demand):
  * **Bẫy Daemon RAM**: Tiến trình Hermes Gateway nền (`python -m hermes_cli.main gateway run`) nạp toàn bộ module vào `sys.modules` trong RAM khi khởi động. Việc sửa file trên đĩa (disk) **HOÀN TOÀN KHÔNG CÓ HIỆU LỰC** đối với Gateway đang chạy nếu tiến trình chưa được restart! Ví dụ: Gateway start lúc 11:28, commit fix lúc 23:43 -> Gateway vẫn chạy logic cũ rích trong RAM, tiếp tục tự động append Advisor gây ức chế cho User.
  * **Kỷ Luật Bắt Buộc Sau Khi Vá Gate**: Sau khi commit sửa bất kỳ logic nào trong `consult_advisor.py`, `advisor_consult.py` hay plugin hook, BẮT BUỘC phải đối soát PID và thời gian khởi động của Gateway (`psutil` / `pgrep`), lập tức restart tiến trình Gateway để giải phóng RAM cũ, nạp code mới. Chi tiết thực nghiệm xem `references/sol-web-tool-calling-and-gateway-restart-audit-20261025.md`.
  * Ngoài ra, các session cũ / in-flight session được mở trước thời điểm commit vẫn mang context cũ, cần kiểm tra timestamp trước khi giải thích.
  * Chi tiết kiến trúc tách biệt fail_streak vs probation xem `references/follow-streak-cooldown-and-probation-ladder-architecture.md`.
- **Masked Key Testing in OmniRoute Pools**: When validating connections under OmniRoute (:20129), do NOT send masked keys (`__Secure****` or `eyJhbG****`) to external endpoints or `/api/providers/validate`. Always use the internal testing endpoint:
  ```http
  POST http://127.0.0.1:20129/api/providers/{connection_id}/test
  ```
  to obtain the live, unmasked validity status.
- **Database vs In-Memory State**: When updating provider connection status in OmniRoute, modifying SQLite directly (`~/.omniroute/storage.sqlite`) does not immediately update the running in-memory cache. Use the REST API:
  ```http
  PUT http://127.0.0.1:20129/api/providers/{connection_id}
  Content-Type: application/json

  {"isActive": true, "testStatus": "active"}
  ```
- **OmniRoute ChatGPT-Web & Sol Worker Pool Rescue Protocol (Cứu Pool Sol / ChatGPT-Web)**:
  * **Hiện tượng nghẽn & lỗi 503 Service Unavailable**:
    * Khi gọi `gpt-web-sol` bị lỗi `HTTP 503: Service Unavailable`, không phải do model Sol hay backend ChatGPT Web bị sập hoàn toàn.
    * **Nguyên nhân cốt lõi (Bẫy Round-Robin dính cụm acc chết)**:
      * Trong combo `gpt-web-sol` thường chứa lượng lớn connections (ví dụ 157 accounts).
      * Khi combo dùng chiến lược `round-robin` với tham số `maxGlobalAttempts` nhỏ (ví dụ 8 attempts), nếu con trỏ round-robin xoay trúng một cụm các tài khoản bị `apiKeyHealth = invalid`, hết hạn cookie `401 auth failed`, hoặc bị OpenAI chặn Turnstile/Sentinel (`ChatGPT blocked the request`).
      * OmniRoute sẽ thử qua 8 tài khoản đầu tiên bị lỗi liên tiếp, vượt quá số lần thử tối đa (`maxGlobalAttempts = 8`) nên lập tức ném lỗi `503 Service Unavailable` ra ngoài, dù trong pool vẫn còn hàng trăm tài khoản khác khỏe mạnh!
    * **Phương án khắc phục kỹ thuật**:
      1. Tăng `maxGlobalAttempts` trong config của combo lên cao hơn (ví dụ 25) và đổi sang `cache-optimized` để tự động bỏ qua các connection đang bị lỗi.
      2. **KỶ LUẬT COOLDOWN (CẤM TẮT VĨNH VIỄN `is_active=0` HOẶC XÓA KHỎI COMBO)**:
         * Khi User yêu cầu "cho cooldown": BẮT BUỘC dùng cơ chế `rate_limited_until = ISO_TIMESTAMP (+30m)` trong `provider_connections`.
         * TUYỆT ĐỐI CẤM set `is_active = 0` hay xóa model entry khỏi combo làm cụt pool tài khoản của User. Tắt là mất luôn tài khoản khỏi pool, khiến hệ thống mất quân và làm hỏng cơ chế bốc thăm tự động.
         * **Cơ chế tự cứu của Cron (`chatgpt-web-pool-healer-watchdog`, ID: `fff7f688990d`)**:
           - Cronjob `cron_chatgpt_web_pool_watchdog.py` chạy định kỳ (mỗi 6h) hoặc khi được kích hoạt.
           - Cron tự động mở profile GPM qua CDP (port 19995), giải captcha/re-login để lấy session token tươi nạp lại vào SQLite.
           - **Pitfall: Bẫy Proxy Egress & False Sentinel**: Nhiều trường hợp tài khoản và cookie trong DB hoàn toàn còn sống, nhưng proxy di động gắn với connection bị timeout (`Proxy Fast-Fail / unreachable`), dẫn đến OmniRoute báo lỗi 503 hoặc Sentinel. Cron test `valid` sẽ bỏ qua không re-login. Đặt `rate_limited_until` cho acc nghỉ 30 phút để proxy hồi phục là phương án chuẩn xác nhất.
         * Quy trình chi tiết tự động cooldown đúng chuẩn xem tại `references/chatgpt-web-pool-cooldown-and-self-healing-protocol.md`.
  * **Bẫy kiểm tra đồng thời (High Concurrency Rate-Limit Trap)**: Khi gửi test tới toàn bộ connections trong pool, TUYỆT ĐỐI CẤM chạy concurrency cao (`max_workers >= 8` gây nghẽn proxy MobiProxy/MikroTik và làm OmniRoute trả về HTTP 500 hàng loạt). BẮT BUỘC dùng concurrency thấp (`max_workers=2`) hoặc chạy tuần tự có sleep 0.2s–0.3s.
  * **Quy trình cứu hộ khép kín (Autonomous Pool Healer)**:
    1. Lấy danh sách connections từ `GET http://127.0.0.1:20129/api/providers`.
    2. Gửi test liveness qua `POST http://127.0.0.1:20129/api/providers/{cid}/test` (kèm payload rỗng `b"{}"`).
    3. Nếu `valid is True` nhưng `isActive is False`: Lập tức gọi `PUT http://127.0.0.1:20129/api/providers/{cid}` với payload `{"isActive": true}`.
    4. Ngay lập tức toàn bộ tài khoản bị cô lập oan sẽ được hồi sinh về trạng thái ACTIVE (100% sống), khôi phục độ trễ phản hồi của `gpt-web-sol` về < 15 giây.
- **Kỷ Luật Thang Leo Thang Worker Khi Sol Gặp Lỗi Mạng (Sol Timeout -> Tier 2 Agy CLI)**:
  * Khi User giao việc sửa code ("thi công đi"): Coordinator CẤM tuyệt đối việc tự ý cowboy patch trong session chính.
  * Soạn sẵn Patch Contract O(1) vào file prompt.
  * Nếu Tier 1 (Sol Worker / `dispatch_worker.py`) gặp lỗi TRANSIENT (stream timeout hoặc ngắt kết nối): CẤM đóng băng và CẤM tự sửa code. BẮT BUỘC kích hoạt ngay **Tier 2 (Antigravity CLI - `ag_cli.py fix`)**:
    ```bash
    python "D:/Taadaa/tools/ag_cli.py" fix --workdir <repo> --file <target_file> "$(cat <prompt_file>)"
    ```
  * Agy CLI sẽ sử dụng pool Antigravity (29 profiles 100% quota) thực thi dứt điểm code delta và tạo test suite focused kiểm chứng offline < 10s.
- **403 QR Validation Boundary (Google Account vs ChatGPT)**:
  * 403 QR Validation xảy ra với **Google Account** (phải mở GPM quét QR bằng camera điện thoại thật), **hoàn toàn KHÔNG liên quan tới ChatGPT hay OpenAI Web accounts**.
  * Không nhầm lẫn hoặc gắn mác lỗi 403 QR cho ChatGPT Web pool.
- **ChatGPT Account Deactivation vs. Gmail Liveness & Automated Purge Invariant**:
  Khi tài khoản ChatGPT-Web báo lỗi `ChatGPT session expired — log into chatgpt.com and copy a fresh cookie`:
  * Tuyệt đối không phán đoán bừa rằng Gmail bị DIE. Phải kiểm tra độc lập qua `checkmail.live` và đăng nhập Google Account.
  * Nếu Google đăng nhập thành công nhưng khi Google SSO vào ChatGPT bị báo `Lỗi xác thực: account_deactivated` ("Bạn không còn tài khoản vì tài khoản đã xóa hoặc vô hiệu hóa"), điều này khẳng định Gmail hoàn toàn LIVE nhưng tài khoản dịch vụ ChatGPT đã bị OpenAI trảm. Không tiếp tục giải Captcha hay ép login lại tốn tài nguyên.
  * **Kỷ luật Loại Trừ Bắt Buộc (Automated Purge Invariant)**: Tài khoản đã bị OpenAI ban thật sự BẮT BUỘC phải được loại trừ triệt để ngay lập tức:
    1. Gọi REST API xóa khỏi OmniRoute: `DELETE http://127.0.0.1:20129/api/providers/{cid}` và xóa khỏi database SQLite.
    2. **Bảo toàn Provider Khác (Selective Provider Guard)**: Chỉ xóa connection có `provider == 'chatgpt-web'`. TUYỆT ĐỐI KHÔNG xóa nhầm connection `antigravity` của cùng email đó vì phiên Google/Antigravity vẫn đang LIVE 100%.
    3. **Loại khỏi Telemetry Alert**: Sau khi purge, gỡ bỏ tài khoản khỏi danh sách `failed_chatgpt` / `all_failed` để triệt tiêu hoàn toàn việc watchdog spam danh sách "Cần chú ý" lên Telegram ở các chu kỳ sau.
  * **Watchdog Submit Button Selector (Chống Click Nhầm SSO/Phone)**:
    Khi điền form login ChatGPT Web, tránh dùng selector chung chung như `button[type="submit"]` vì có thể click nhầm vào các nút "Continue with Google/Apple/Microsoft/Phone". Bắt buộc lọc text DOM để loại trừ các nút SSO trước khi click.
  * **Closeout Gate Fast-Path Khi Reviewer Timeout (> 60s)**:
    Khi chạy `closeout_gate.py` cho các repo lớn, nếu model mặc định `review` bị nghẽn (do tải round-robin ChatGPT Web), hãy chuyển sang `--model ag-gemini-pool-3` (độ trễ ~3-5s) và sử dụng `--input <diff_file>` sau khi đã chạy verified focused test để hoàn tất thẩm định chốt phiên trong ngân sách 60s của Coordinator.
- **reCAPTCHA Enterprise Audio Solver & Detached Frame Pitfall**:
  Khi tự động hóa đăng nhập Google trong GPM gặp thử thách reCAPTCHA Enterprise:
  * Sử dụng phương pháp giải âm thanh `solve_recaptcha_audio` qua `speech_recognition` và `pydub`.
  * **Pitfall**: Sau khi click nút `#recaptcha-audio-button`, frame challenge của Google có thể reload/navigate khiến biến `bframe` cũ bị detached (`Locator.count: Frame was detached`). BẮT BUỘC phải re-acquire lại `bframe` từ `page.frames` ngay sau khi click trước khi truy vấn selector `#audio-source`.
- **OmniRoute HTTP SSE Streaming Invariant (`stream=True`)**:
  Khi gửi prompt cho `gpt-web-sol` hoặc `chatgpt-web/gpt-5.6-sol-high` qua OmniRoute (`http://127.0.0.1:20129/v1/chat/completions`):
  * **CẤM DÙNG `stream: false`**: Chế độ non-streaming chờ toàn bộ payload từ CDP ngầm, gây nghẽn buffer và dẫn tới timeout (> 60s/120s) làm sập lệnh thẩm định của Coordinator / Closeout Gate.
  * **BẮT BUỘC BẬT `stream: true`**: Luồng HTTP Server-Sent Events (SSE) đẩy chunk `choices[0].delta.content` ngay từ giây thứ 3–5, triệt tiêu hoàn toàn nghẽn I/O và hoàn tất đánh giá trong < 30s.

## Worker & Subagent Dispatch Protocol (Coordinator vs Worker)
- **Kỷ Luật Worker Floor 300s Bắt Buộc**:
  * Khi gọi bất kỳ worker nào (`dispatch_worker.py`, `sol_worker.py`), Coordinator BẮT BUỘC tuân thủ sàn `timeout >= 300s`. CẤM TUYỆT ĐỐI tự ý gõ cờ `--timeout` ngắn (ví dụ 30s) trong terminal làm ngắt ngang khi model worker đang suy nghĩ / stream.
- **CẤM TUYỆT ĐỐI Hermes Native Delegation (`delegate_task`)**:
  Coordinator tuyệt đối không được gọi `delegate_task` để spawn subagent bừa bãi. Việc spawn subagent tự do gây bloat context, ngâm timeout 600s làm nghẽn event loop của gateway, vi phạm sandbox và phá vỡ kiểm soát phân vai của farm.
- **Quy chuẩn ủy quyền Worker (Farm Worker CLI & Fallback Ladder)**:
  Khi cần thực hiện các task sửa code / điều tra sâu vượt quá ngân sách Coordinator O(1):
  * **Tier 0 (Primary Promo - Free 100% tới 31/10):** Qoder Worker (`D:/Taadaa/tools/qoder_worker.py` - model DeepSeek-Flash). Đứng đầu bậc thang để ăn trọn đợt promo miễn phí token. Tự sửa file trực tiếp (`--dangerously-skip-permissions`), kiểm tra AST syntax trước khi kết luận.
  * **Tier 1 (Fallback 1):** BẮT BUỘC dispatch qua `python D:/Taadaa/tools/sol_worker.py "<contract O(1)>" --workdir <repo>` (hoặc qua `dispatch_worker.py`).
  * **Tier 2 (Fallback 2):** `ag_cli.py fix` (Antigravity pool) - CHỈ KÍCH HOẠT khi Qoder và Sol Worker thất bại có receipt audit ghi vào `dispatch.jsonl`.
  * **Tier 3 (Fallback 3):** Haiku / Claude CLI (`haiku_worker.py` / `claude_worker.py`) - CHỈ KÍCH HOẠT khi Qoder, Sol VÀ Agy đều thất bại có receipt audit trong cùng correlation session, hoặc khi có cờ `--on-demand` từ User.
  * **Kỷ Luật Timeout Worker & Benchmark Bắt Buộc (Floor 480s)**:
    - Khi chạy worker thi công hoặc tổ chức benchmark so tài giữa các model, Coordinator **CẤM TUYỆT ĐỐI** tự ý bóp timeout xuống ngắn (30s/50s/60s) gây lỗi văng timeout giả (false-positive timeout) khi model đang chạy CoT suy luận sâu.
    - Sàn timeout BẮT BUỘC: `timeout >= 480s` (8 phút) cho cả worker lẫn benchmark thực chiến.
  * **Cơ chế Synthetic Tool Calling vs Payload Overflow (Coordinator vs Web Worker)**:
    - OmniRoute hỗ trợ Synthetic Tool-Calling (`open-sse/translator/webTools.ts`) cho các web model (chuyển đổi tools thành prompt và parse `<tool>` ngược lại).
    - Sol Web (`chatgpt-web`) thất bại khi làm Coordinator vì request của Hermes chứa toàn bộ system prompt + 15 tool schemas (~100k-200k chars), vượt quá request body limit của Web UI gây lỗi `413 Payload Too Large`.
    - Gemini/Codex làm Coordinator được vì context window đạt 1M-2M tokens, nuốt trọn payload mà không bị nghẽn.
    - **Lý Do Tuyệt Đối Không Thể Đưa Gemini Web Argon 4 Lên Làm Coordinator (Web Session Limitations)**:
      * **Thiếu Native Function Calling**: Backend `gemini-web.ts` chạy qua Reverse Headless Stream của web UI `gemini.google.com` (chỉ có `StreamGenerate`), không hỗ trợ chuẩn OpenAI Tool-Calling / Function Call native. Ở tầng Worker, Argon 4 chạy được là nhờ ReAct wrapper (`gemini_web_worker.py`) bóc tách chuỗi regex; nhưng ở tầng Coordinator của Hermes, ngữ cảnh đồ sộ 15+ JSON tool schemas sẽ khiến model web không thể emit tool call hợp lệ.
      * **Bóp nghẽn Context Window (Rolling Session Drop)**: Web session của Google tự động cắt gọt hoặc tóm tắt ngữ cảnh khi vượt ngưỡng, làm Coordinator bị mất trí nhớ về rules, database schema và instruction của User.
      * **Độ bền luồng Stream qua Proxy Mobi 4G**: Các turn suy luận dài và sâu của Coordinator rất dễ bị timeout ngắt kết nối (`disconnect: request_signal_aborted / hedge-cancelled`), làm đứt gãy phiên hội thoại Telegram.
      * **Phân định rạch ròi**: **Antigravity Pool (Gemini 3.8 Flash High qua Code Assist IDE API)** giữ vai trò Coordinator tối cao (1M tokens, native tools, context cache tức thì); **Gemini Web Argon 4** và **Qoder (DeepSeek-Flash)** độc quyền làm Worker Tiên phong phản ứng nhanh.
    - Qoder CLI có adapter trong OmniRoute (`open-sse/executors/qoder.ts`), chạy được chat qua `--config-dir C:\Users\Kibe\.omniroute\qoder-cli`. Làm Autonomous Worker trực tiếp qua `qoder_worker.py` là mô hình ổn định nhất.
    * **Lưu ý về Gemini Web / Argon Pool (`gemini-web-argon-pool` trên :20129) & Gemini Web Worker**:
      - **Bản chất kỹ thuật**: Model category = 3 trong backend `gemini-web.ts` nối với Google Web Session. Trên UI OmniRoute hiển thị nhãn legacy là `gemini-3.1-pro`, nhưng thực tế backend đang map tới flagship Google Gemini 4 (Argon).
      - **Khả năng làm Autonomous Worker qua `gemini_web_worker.py`**:
        * Gemini Web bản chất không có native tool calling (chỉ hỗ trợ `StreamGenerate`).
        * Tuy nhiên, hoàn toàn có thể chạy làm Autonomous ReAct Worker thông qua harness bọc ngoài `D:/Taadaa/tools/gemini_web_worker.py`.
        * Harness này cung cấp prompt contract chống kích hoạt python sandbox nội bộ của web Google, đồng thời parser được tối ưu nhận diện cả chuẩn ReAct (`ACTION: PATCH`, `ACTION: READ_FILE`, `ACTION: COMMAND`, `ACTION: DONE`) lẫn cú pháp diff 4 góc đặc trưng của Gemini (`PATCH <file>\n<<<<\n...\n====\n...\n>>>>`).
        * Kèm atomic write, AST syntax verification rollback tức thì và cơ chế cấm `DONE` nếu chưa vượt qua verification test command.
      - **Giới hạn rolling window**: Bị Google áp giới hạn ~50-100 requests Pro / chu kỳ 3-4 giờ trên từng account. Cần duy trì qua pool 5 accs kẹp proxy 4G Mobi 1-1 theo chiến lược `cache-optimized` để tránh nghẽn.
      - **So sánh thực chiến**: Khi làm worker thi công code tự động, Agy CLI (với Gemini 3.8 Flash + native tool calling + xoay tua 22 profile local) có ưu thế về workspace agent; nhưng `gemini_web_worker.py` (Argon 4) đã chứng minh khả năng phản hồi siêu tốc (trung bình ~11.2s), sửa diff O(1) chuẩn xác và đè bẹp Agy CLI (thắng 5-0 trong giải đấu Benchmark 5 trận thực tế ngày 28/10/2026). Chi tiết giải đấu xem `references/gemini-argon-vs-agy-cli-5rounds-benchmark.md`, phân tích rào cản Coordinator tại `references/argon-web-vs-coordinator-architecture-limitations.md` và kiến trúc worker tại `references/gemini-web-worker-architecture.md`.
    - **Kỷ Luật Thực Thi Dứt Điểm (Chống Hỏi Lại / Chống Chần Chừ Khi User Ra Lệnh)**:
      * Khi User đã phát lệnh trực tiếp ("làm đi", "chạy đi", "thi đấu cho tao", "bảo làm thì làm đi đừng hỏi lại"): Coordinator **CẤM TUYỆT ĐỐI** kết thúc bằng câu hỏi xác nhận ("Em bắt đầu nhé?", "Anh có muốn...").
      * Mọi quyền đã được cấp sẵn. Coordinator BẮT BUỘC thực thi hành động ngay lập tức trong cùng turn và trả về bằng chứng thực tế. Do dự hoặc hỏi lại bị coi là vi phạm nghiêm trọng kỷ luật điều phối.
    - **Kỷ Luật Timeout Benchmark Chuẩn Worker (Floor 360s)**:
      * Khi tổ chức thi đấu / benchmark so tài model hay worker sửa code, Coordinator **CẤM TUYỆT ĐỐI** tự ý bóp timeout xuống 60s/75s để test nhanh.
      * Timeout benchmark BẮT BUỘC đặt sàn tối thiểu 360s như worker tiêu chuẩn để phản ánh chính xác năng lực suy luận thực tế và tránh làm fail giả (false timeout) khi model đang bootstrap CLI hoặc giải bài toán khó.
    - **Tier 0 Qoder Worker Integration (`dispatch_worker.py`)**:
      * Đã tích hợp Qoder Worker (`D:/Taadaa/tools/qoder_worker.py`) làm Tier 0 trong `dispatch_worker.py` với cờ opt-in an toàn `ENABLE_QODER_WORKER=1`.
      * Khi Qoder gặp sự cố (timeout, không có diff, lỗi tiến trình), dispatcher tự động ghi audit và kích hoạt fallback sang Sol Worker (Tier 1) rồi đến Agy CLI (Tier 2).
    - **Đặc tính kỹ thuật Hardcore Farm Engineering (Argon 4 vs Agy CLI vs Sol Web)**:
      * **Argon 4 (Gemini Web Pool)**: Phản xạ siêu tốc (10s – 30s), cực mạnh về thuật toán phân phối tải, concurrency sliding window. Nhược điểm: Dễ dính lỗi ẩu thay đổi API/structure cũ (tự ý tạo Enum hoặc đổi tên thuộc tính) hoặc bỏ sót corner-case nhỏ (`normalize_text(None)`). Thích hợp làm Worker phản ứng nhanh, fix bug nóng.
      * **Antigravity CLI (Agy 3.8 Flash)**: Tốc độ chậm hơn (1 – 4 phút do CLI runtime), nhưng lập trình phòng thủ cực cao (defensive programming), giữ vững 100% backward compatibility, xử lý corner cases mẫu mực (thắng 2-1 ở giải đấu Hardcore BO3 ngày 28/10/2026). Thích hợp làm Architect Worker cho refactor phức tạp. Chi tiết xem `references/gemini-argon-vs-agy-cli-hardcore-bo3-benchmark.md`.
      * **ChatGPT Web Sol High vs Argon 4**: Ở giải derby micro-surgery (28/10/2026), Argon 4 thắng 5-0 nhờ tốc độ vượt trội (18.6s vs 30.8s) và độ ổn định proxy 100%, trong khi Sol Web bị dính 2 lần 503 do cụm acc chết trong combo round-robin. Chi tiết thực nghiệm xem `references/gemini-argon-vs-sol-web-derby-benchmark.md`.
  * Coordinator giữ vai trò nghiệm thu O(1) qua focused test và canary thực tế; cấm spawn subagent mò mẫm file.
- **Cơ chế Auto-Rewire Cứng Chống Nhảy Cóc Sang Claude (`haiku_worker.py`)**:
  * Claude CLI / Claude Worker là **100% On-Demand**. Tuyệt đối **CẤM** Coordinator tự ý đề xuất hoặc gọi `haiku_worker.py` / `claude_worker.py` theo quán tính/phản xạ khi User chưa yêu cầu đích danh.
  * **CẤM TỰ TRUYỀN CỜ `--on-demand` (Anti-Rogue Invariant)**: Tuyệt đối CẤM Coordinator tự động tiêm cờ `--on-demand` vào lệnh gọi Claude Worker khi User chỉ phát các lệnh chung như "làm đi", "sửa đi", "tiếp tục". Cờ `--on-demand` CHỈ ĐƯỢC PHÉP dùng khi tin nhắn gốc của User có chứa đích danh từ khóa `"claude"`.
  * Khi Sol (Tier 1) và Agy (Tier 2) đều fail hoặc timeout: Coordinator BẮT BUỘC dừng lại báo cáo trung thực biên bản kèm log audit, TUYỆT ĐỐI CẤM tự ý nhảy cóc sang Claude Worker để lấp liếm lỗi của Sol/Agy.
  * **Hard Auto-Rewire Gate:** `haiku_worker.py` kiểm tra cờ `--on-demand`, `--from-dispatch` và `USER_ON_DEMAND_CLAUDE=1`. Nếu không có, script lập tức chặn đứng việc gọi Claude và **tự động bẻ lái (rewire) 100%** toàn bộ tham số sang `dispatch_worker.py` để ép chạy Sol (Tier 1) $\to$ Agy (Tier 2) trước.
  * Khi Sol Worker (:20129) bị timeout hoặc nghẽn mạng: Nếu Coordinator đã có exact patch O(1) (<= 30 dòng, <= 2 files), Coordinator **được quyền thực hiện Emergency Surgery (L2) trực tiếp** bằng `patch` tool kèm focused test. Tuyệt đối KHÔNG tự động chuyển sang Claude Worker rồi báo User như một phản xạ mặc định.
- **Kỷ Luật Định Dạng Tin Nhắn Telegram (Chống Rò Rỉ Mã LaTeX Thô)**:
  * Parser của Telegram và Gateway không hỗ trợ render MathJax / LaTeX math blocks (`$$ ... $$`).
  * Tuyệt đối **CẤM** Coordinator gửi các thẻ công thức toán LaTeX như `\textbf{...}`, `\longrightarrow`, `\longleftarrow`, `\implies`, `\iff`, `\rightarrow`. Các mã này sẽ bị in nguyên văn ra màn hình điện thoại của User gây phản cảm.
  * Luôn sử dụng cú pháp Markdown chuẩn (`**chữ đậm**`) và mũi tên Unicode tự nhiên (`→` hoặc `->`) trong mọi tin nhắn trả lời User.

## Phân Tầng Reviewer & Kỷ Luật Quota Guard (Reviewer Hierarchy)
Trong hệ thống Taadaa Farm, vai trò Reviewer được phân định rạch ròi theo 2 kịch bản:

### 1. Kịch bản A: Thẩm Định Chốt Phiên (Closeout Gate Pipeline)
- **Tier 1 (Độc quyền xử lý đầu tiên — First-Responder Monopoly):** Sol High (`:20129` qua `sol_repair.py`). Khi Reviewer chấm điểm trượt (Strike 1 & Strike 2), Sol High độc quyền tạo bản vá O(1) <= 30 dòng. Cấm tự ý dispatch Worker mò mẫm khi Sol chưa hỏng.
- **Kỷ Luật Auto-Remediation (Cấm khóc lóc / phân trần / hỏi User khi Gate DENY):**
  * Khi `closeout_gate.py` trả về `REJECTED` (score < 80/85): **TUYỆT ĐỐI CẤM** dừng lại, khóc lóc, phân trần hoặc hỏi User "có nên tiếp tục / override không".
  * Gate DENY là **Action-Forcing Pivot**: Bắt buộc đọc ngay `key_findings` và `judge_notes` của Reviewer scorecard.
  * Tự động sửa dứt điểm các lỗi Reviewer chỉ ra (logic bounds, thứ tự check fallback, structured telemetry logging, caplog tests).
  * Chạy test focused verify $\to$ commit $\to$ chạy lại `closeout_gate.py` lặp lại vòng lặp cho đến khi đạt `APPROVED` (>= 80/85, Grace band 80-84 được duyệt).
- **Tier 2 (Fallback tự động):** Worker Gateway (`dispatch_worker.py` điều phối Agy CLI / Claude Haiku). Chỉ kích hoạt khi Sol Repair exit != 0, crash, timeout hoặc diff > 30 dòng.
- **Tier 3 (Strike 3 Hand-off):** Claude CLI (`claude_worker.py --role reviewer` / Claude Sonnet). Nếu trượt 3 lần liên tiếp trên cùng scope_hash, toàn bộ hệ thống dừng lại và chuyển giao quyền can thiệp cho Claude Sonnet.

### 2. Kịch bản B: Tư Vấn & Review Kỹ Thuật Khi Đang Chạy (On-Demand Reviewer)
- **Tier 1 (Ưu tiên số 1): Sol Advisor (`:20129` qua `consult_advisor.py`):**
  * 100% On-Demand, miễn phí token, phản hồi siêu tốc (< 35s), nắm vững bối cảnh và quy chuẩn an toàn Farm.
  * Khi User yêu cầu review nhanh hoặc khi Claude gặp sự cố quota: Gọi Sol Advisor là phương án mặc định.
- **Tier 2 (Thẩm định chuyên sâu): Claude CLI Reviewer (`claude_worker.py --role reviewer`):**
  * Sử dụng Claude Sonnet chạy read-only (`--disallowedTools Edit,Write,NotebookEdit`), turns cap 10-20.
  * Phục vụ các ca audit bảo mật, forensic lỗi sâu và thiết kế kiến trúc phức tạp.

### 3. Kỷ Luật Xử Lý Khi Claude Quota Guard Chặn (Exit 20 / 22)
- Khi Quota 5 giờ >= 85% hoặc Quota tuần >= 90%, `claude_quota_guard.py` sẽ lập tức chặn lệnh gọi Claude CLI.
- **CẤM TỰ VƯỢT RÀO:** Guard đã cài đặt cơ chế chống Agent tự bypass (chặn automated caller dùng `--force-claude`, `--user-approved`, env `CLAUDE_USER_APPROVED=1` hay lệnh `allow`). Chỉ User là con người mới có quyền mở khóa.
- **Quy tắc chuyển hướng O(1) (Clean Pivot):** Khi gặp `CLAUDE_QUOTA_GUARD_BLOCKED`, Coordinator CẤM vòng vo thử lại hoặc cố vượt rào; BẮT BUỘC chuyển hướng ngay lập tức sang **Sol Advisor (:20129)** để hoàn thành việc review/tư vấn mà không làm gián đoạn tiến độ phiên làm việc!


