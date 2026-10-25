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
- **Quy chuẩn ủy quyền Worker (Farm Worker CLI)**:
  Khi cần thực hiện các task sửa code / điều tra sâu vượt quá ngân sách Coordinator O(1):
  * **First Responder:** BẮT BUỘC dispatch qua `python D:/Taadaa/tools/sol_worker.py "<contract O(1)>" --workdir <repo>` (hoặc chỉ định `--model`, `--timeout`).
  * **Fallback:** Sử dụng `python D:/Taadaa/tools/dispatch_worker.py`.
  * Coordinator giữ vai trò nghiệm thu O(1) qua focused test và canary thực tế; cấm spawn subagent mò mẫm file.
- **Chống Phản Xạ Gọi Claude Worker (Anti-Reflex Claude Dispatch)**:
  * Claude CLI / Claude Worker là **100% On-Demand**. Tuyệt đối **CẤM** Coordinator tự ý đề xuất hoặc gọi `claude_worker.py` theo quán tính/phản xạ khi User chưa yêu cầu đích danh.
  * Khi Sol Worker (:20129) bị timeout hoặc nghẽn mạng: Nếu Coordinator đã có exact patch O(1) (<= 30 dòng, <= 2 files), Coordinator **được quyền thực hiện Emergency Surgery (L2) trực tiếp** bằng `patch` tool kèm focused test. Tuyệt đối KHÔNG tự động chuyển sang Claude Worker rồi báo User như một phản xạ mặc định.

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


