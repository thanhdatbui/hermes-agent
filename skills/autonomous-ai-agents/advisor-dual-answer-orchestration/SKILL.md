---
name: advisor-dual-answer-orchestration
description: "Use when user asks Hermes for advice to get dual answers."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [advisor, orchestration, dual-answer, canary, intent-routing, sol]
    related_skills: [hermes-agent, verification-evidence, agent-review-loops]
---

# Advisor Dual-Answer Orchestration

Use this skill when the user distinguishes **asking Hermes for advice** from issuing an imperative command. The required behavior is not merely exposing an `advisor_consult` tool: Hermes must automatically return the primary model's answer together with a read-only Advisor answer in the same response.

## Core contract

### Advice intent

Classify the original user message conservatively and deterministically:

- Advice/question intent: a question mark or explicit advice markers such as `tư vấn`, `lời khuyên`, `nên`, `có nên`, `theo mày`, `đánh giá`, `phân tích giúp`, `what should`, `should I`, `advise me`, or colloquial evaluative questions asking for comparison/cause/feasibility/strategy (e.g., `sao nhìn ...`, `tại sao ...`, `sao lại ...`, `sao thế ...`, `nhìn thế nào`, `sao ... lỏ/phèn thế`, `... đc k nhỉ`, `... có nên ... k`, `... đúng k?`, `... hay là do ...`, `... hay như v lâu quá`). When user questions system mechanics, algorithm behavior, or farm strategy rather than giving an execution command, treat strictly as advice intent and proactively provide the Advisor Sol dual-answer without waiting for user prompt.
- Imperative/work intent: `chạy`, `sửa`, `kiểm tra`, `đăng ký`, `upload`, `restart`, `làm đi`, or equivalent execution requests without a genuine decision question.
- Empty, synthetic continuation, and intermediate tool-loop messages are never advice intent.

Do not infer advice intent only because a task is technically difficult. The trigger is the user's conversational intent: asking for judgment/advice rather than directing execution.

### Response behavior

For an advice-intent turn:

1. **Mandatory Execution & Mechanical Enforcement:** 
   - The Coordinator must never emit a solo answer on advice intent.
   - Use `python D:/Taadaa/tools/consult_advisor.py "<prompt>"` (hoặc `ensure_dual_answer`) để gọi trực tiếp Advisor Sol-WebPool, cấm tự viết code gọi HTTP trần.
2. Direct Sol Route with Increased Wait Time:
   - Call directly to OmniRoute :20129 `gpt-web-sol` (ChatGPT-Web Pool 115 accounts). CẤM gọi `gpt-5.6-sol` (trỏ nhầm OpenAI API lỗi 402).
   - Timeout raised to 45s to allow reasoning models sufficient TTFT and token completion.
   - Fail-safe: If Sol times out or hits pool limits, FAIL CLEANLY and output `Advisor: unavailable` immediately. DO NOT fallback to Gemini or 9Router. Primary coordinator answer is sufficient.
3. Strict Safety & Comprehensive Redaction:
   - Payload includes `tools: []` and `tool_choice: "none"`.
   - All credentials, API keys (`sk-...`), Bearer tokens, HTTP Basic Auth `://user:pass@`, JSON fields (`{"password": "...", "api_key": "..."}`), unquoted Vietnamese `mật khẩu là abc`, and field tokens (`token=...`, `sessionid=...`, `session_id=...`) are automatically redacted before transmission.
   - Advice length is bounded to 2,500 characters.
   - Pseudo-200 usage limits (`[Error: You've hit your limit]`) are filtered on all tiers.
   - Requires explicit `data: [DONE]` marker on stream; premature socket closure triggers clean fallback instead of accepting truncated advice.
4. Robust Intent Classification:
   - Captures compound intents (commands followed by advice queries like `chạy batch rồi cho tao biết nên làm gì`, `git log xem có gì lạ không`).
   - Captures evaluative cause queries (`vì sao`, `thấy sao`).
   - Excludes false-positives from `review`/`plan` commands (`chạy lại review combo`, `lên plan cho phase 2`) and nouns containing 'liệu' (`dữ liệu`, `tài liệu`, `vật liệu`) from tripping `\bliệu\b`.
5. Append the script's exact output block at the end of the response:

   ```text
   --- Advisor (Sol / review) ---
   <structured advice or bounded raw advice>
   ```

   If Advisor is unavailable, state `Advisor: unavailable (Sol / review timeout hoặc pool limit; chỉ hiển thị câu trả lời Coordinator)`.
6. Advice is not approval, execution, or a closeout verdict. The Coordinator still owns the decision and must obey farm safety, worker, and closeout gates.

### Advice-to-Action Transition Flow ("R làm đi" vs "Gọi sol plan")

When an advice-intent turn presents a diagnosis and proposed remediation:
1. **User directs execution directly ("R làm đi", "Làm luôn đi", "Triển khai đi", "Fix đi", "Ok duyệt"):**
   - Strictly Imperative: Do NOT call Advisor again; user approved direction.
   - Immediate Tiered Execution: focused test -> O(1) patch -> delegate worker -> verify.
2. **User asks Advisor for plan ("Gọi sol plan", "Sol lên plan", "Nhờ Sol vẽ kiến trúc"):**
   - Explicit Planning Intent: User specifically pauses execution to request an architectural blueprint from Advisor Sol before coding starts.
   - Plan Generation Guard (avoiding 60s timeout): Claude Opus Thinking on 9Router has high reasoning latency. Generating a monolithic plan easily hits the host's 60s terminal timeout (`Exit 124`). Prompt Sol for high-density, concise bullet points and code skeletons (<40 lines per section), or break into focused queries (e.g., Section 1: Architecture & Guards, Section 2: Roadmap & Immediate Actions).

## Advisor safety boundary

The Advisor is read-only and advisory:

- No tools, shell, ADB, UI, filesystem, worker dispatch, commit, push, or account mutation.
- Request payload must use `tools: []`, `tool_choice: "none"`, and the existing `review` model/combo.
- A timeout or transport error is `unavailable`, not a rejection and not permission to fabricate a recommendation.
- Cap one automatic Advisor call per user turn. Never trigger recursively from the Advisor response or from intermediate tool calls.

## Implementation shape

Keep the adapter separate from orchestration:

- Adapter: synchronous `advisor_consult` with secret redaction, bounded timeout, structured status, raw-advice bound, and telemetry.
- Orchestrator: advice-intent classifier, post-primary composition helper, one-call guard, and unavailable fallback.
- Tests: offline mocked tests for classifier positives/negatives, primary+Advisor composition, unavailable preservation, and one-call cap.

Do not confuse a direct adapter probe with proof that the Coordinator automatically triggers the Advisor. The latter requires a dispatch-boundary canary.

## Verification and canary gate

A valid acceptance sequence is:

1. Focused offline mocked tests pass after the final edit.
2. Import/compile and scoped diff checks pass.
3. Direct route probe confirms `review` connectivity separately.
4. Orchestration canary sends a synthetic hard advice question through the Coordinator/model-tool dispatch boundary and proves:
   - advice intent is detected;
   - the primary answer remains present;
   - an `Advisor (Sol / review)` section is appended on success;
   - the Advisor is called once only;
   - a normal imperative command does not call Advisor;
   - an unavailable Advisor leaves the primary answer intact.
5. Do not report `DONE` from adapter status alone. If only the adapter canary passes, report `adapter PASS; orchestration canary pending`.

See `references/dual-answer-canary.md` for the concrete evidence matrix and failure classifications.
See `references/pure-sol-discipline-and-clean-fail-20261010.md` for the Operator policy: pure Sol route only (:20129 review), timeout >= 45s, clean fail to unavailable without messy Gemini/9Router fallbacks.
See `references/claude-cli-review-loop-and-mechanical-advisor-enforcement.md` for the 4-round Claude CLI review progression (62 -> 72 -> 86 -> 91 APPROVED), 3-tier fallback architecture, leak-proof redaction engine, and classifier edge cases.
See `references/mechanical-dual-answer-enforcement-and-stream-deadline-audit-20261010.md` for intent classification matrix, stream wall-clock deadline handling, and mechanical enforcement gate.

## Common failure modes

- **Colloquial evaluative questions without question mark (?):** Questions starting with `sao ...` ending in `v`, `vậy`, `thế`, `ấy`, `hả` or describing instability (e.g. `sao bên farm kibe các máy cứ tắt r onl đc liên tục trên xiaowei v, k ổn định ấy`) are evaluative cause questions. Classifier must capture non-adjacent `sao ... (cứ|lại|bị|mất|rớt)` and ending particles `v/vậy/thế/ấy` even without `?`.
- **CLI prompt containing 'adb' tripping Hard Gate #5:** When calling `advisor_consult.py` with `--query` or `--context` containing device strings like `adb` or device error logs directly on the terminal CLI, the shell command can trip `guard_device_bulkhead.py` (which intercepts terminal commands containing `adb` without `-s <serial>`). Best practice: serialize prompt/context into a temporary JSON file (e.g. `D:/Taadaa/tmp/advisor_input.json`) and call Python `consult_advisor` via script import, avoiding passing bare `adb` text in shell arguments.
- **CẤM fallback lai tạp sang Gemini / 9Router khi gọi Advisor Sol:** Khi user yêu cầu Advisor Sol, Advisor CHỈ LÀ Sol (:20129 route `review` hoặc direct model `gpt-web-sol`). Tuyệt đối KHÔNG tự ý fallback sang Gemini (`ag-gemini-pool-3`) hay 9Router rồi gán ghép danh xưng lộn xộn ("Sol Gemini High", "Sol Backup 9Router"). Nếu Sol timeout (>45s) hoặc lỗi pool, FAIL CLEANLY ngay và báo `Advisor: unavailable (Sol / review timeout hoặc pool limit; chỉ hiển thị câu trả lời Coordinator)`. Tuyệt đối trung thực, cấm mạo danh danh xưng Advisor.
- **BẪY NHẦM MODEL ID 'gpt-5.6-sol' VS 'gpt-web-sol' (HTTP 402):** Trong OmniRoute (:20129), pool gần 100 tài khoản ChatGPT-Web (chính xác 115 accounts, 111 active) được đặt tên route chuẩn là `gpt-web-sol` (hoặc combo `chatgpt-web-pool` / `review`). Tên gọi `gpt-5.6-sol` là route trỏ vào OpenAI direct API key (đã hết credit -> trả về HTTP 402 Payment Required). Khi gọi Advisor Sol, BẮT BUỘC dùng model ID `gpt-web-sol` hoặc `review`, CẤM gõ `gpt-5.6-sol` dẫn đến hiểu lầm là pool web bị cạn quota.
- **Tăng wait time cho Sol (timeout >= 45s):** Sol Web High là reasoning model chuyên sâu qua web pool, TTFT cần 15–35s để suy nghĩ. Cấm đặt timeout quá ngắn (4–10s) dẫn đến false-negative timeout liên tục. Bắt buộc để timeout tối thiểu 45s với streaming (`stream: true`).
- **Trôi dạt thói quen tự trả lời một mình & Lệnh 'gọi advisor plan trc' (Operator Chấn Chỉnh):** Khi User hỏi câu hỏi phân tích nguyên nhân/hệ thống ('là sao cứ lệch hoài thế', 'tại sao ...'), Coordinator rất dễ bị quán tính trả lời solo bằng primary voice. User bức xúc nhắc nhở: 'sao bữa nay t đéo hề thấy mày gọi advisor nữa?' và 'gọi advisor plan trc'. BẮT BUỘC: Mọi câu hỏi thắc mắc nguyên nhân lỗi hệ thống/niche/farm đều phải trigger Advisor dual-answer, và khi chuyển sang giải pháp kiến trúc phải lấy blueprint từ Advisor Sol trước khi đụng code.
- **Answering deep strategy/algorithm questions solo without Advisor:** When user asks evaluative questions about farm mechanics, algorithm causes, or policy adjustments (e.g., 'tại sao nghỉ 7 ngày vẫn bị cấm', 'có nên nâng cooldown lên 15d k', 'có phải do bug verify cũ k', 'đc k nhỉ'), Coordinator often falls into answering purely in primary model voice and forgets to trigger Advisor Sol until user explicitly complains ('sao nãy h t hỏi mày mà mày k đưa góc nhìn advisor v'). Always trigger Advisor Sol automatically for evaluative strategy/cause questions.
- **Tool exists but never auto-triggers:** registering `advisor_consult` in the tool catalog proves availability, not user-intent routing. Add and test the post-primary orchestration seam.
- **Calling Advisor before the primary answer:** this changes the primary workflow and can make the response dependent on Advisor latency. Compose after the primary final answer.
- **Calling Advisor for every command:** adds 15–45 seconds to routine farm operations and violates the user's distinction between asking and ordering.
- **Reporting a direct Sol answer as dual-answer success:** a direct Advisor response is not evidence that the primary model answered or that composition occurred.
- **Treating timeout as rejection:** keep the primary answer and label Advisor unavailable.
- **False-negative timeout from tight thresholds & non-streaming calls on reasoning models:** Sol Web High (`review` combo) and reasoning fallbacks (`terra-high`, `opus-thinking`) run deep reasoning and typically take 25–45 seconds before emitting text. Non-streaming HTTP calls block until completion finishes, frequently timing out against 45–55s socket limits. Always invoke with `stream: true` (SSE streaming) and consume chunks progressively to maintain socket activity and prevent premature idle-read timeouts. On hosts with foreground terminal execution guards, any command with `timeout > 60s` triggers `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`; clamp probe/adapter foreground timeouts strictly to <= 60s (e.g. 50–55s socket timeout, 60s terminal timeout) or run via `background=True`.
- **Handling web pool rate limits in review combo:** When Tier 0 (`chatgpt-web-pool`) returns usage limits (`[Error: You've hit your limit]`), ensure failover correctly routes to Tier 1 (`codex/gpt-5.6-terra-high` or `ag-opus-pool`) rather than returning the limit error text as a final response.
- **Upstream pseudo-200 limit masking & reasoning timeout waterfall:** See `references/omniroute-web-pseudo-200-and-reasoning-timeouts.md` for details on:
  1. ChatGPT-Web returning HTTP 200 with text `[Error: You've hit your limit...]` which fools OmniRoute combos into thinking the call succeeded, blocking rotation across remaining pool accounts. Fixed in OmniRoute `validateQuality.ts` by rejecting `[Error: ` as an invalid quality / upstream error to trigger automatic failover across pool accounts.
  2. Mismatch between 8s target timeout in `ag-opus-pool` config vs 25-45s reasoning TTFT, combined with cumulative waterfall exceeding 60s foreground limits. Resolved by calibrating `targetTimeoutMs: 60000` (60s) for `ag-opus-pool` and `review` in `storage.sqlite`.
  3. **Permanent Cooldown Flag Wiring (§5):** When quality check rejects pseudo-200 limit in `handleRoundRobinCombo` and `handleComboChatInner`, actively call `recordProviderCooldown(provider, target.connectionId, resilienceSettings)`. In `storage.sqlite`, enable `resilienceSettings.providerCooldown.enabled = true` with min 5m / max 2h cooldown so exhausted accounts are excluded in $O(1)$ on subsequent requests instead of incurring 20s hold penalties repeatedly.
- **CẤM TUYỆT ĐỐI fallback sang ag-gemini-pool-3:** Khi gọi Advisor Sol, nếu `gpt-web-sol` hoặc combo `review` timeout hoặc lỗi pool, BẮT BUỘC FAIL CLEANLY và báo `Advisor: unavailable`. TUYỆT ĐỐI CẤM fallback sang `ag-gemini-pool-3` rồi gán nhãn là Advisor Sol (vi phạm nghiêm trọng kỷ luật trung thực của hệ thống).
- **`ALL_TARGETS_SKIPPED` on `ag-gemini-pool-3`:** This error means all Gemini pro accounts are quota-exhausted at that moment. Symptom: `poolSize: 22, attempted: 0`. Do NOT retry — treat as unavailable and serve primary answer only, label `Advisor: unavailable (quota exhausted, primary answer shown)`.
- **Pool rotation waterfall & client-side abort (Why 90+ accounts still fail/fallback):** When multiple web accounts are exhausted within the same 3-hour window, OmniRoute actively rotates across accounts via atomic in-memory `rrCounters`. However, each exhausted account takes 15–23s of keepalive streaming before emitting the limit chunk. Trying just 2 exhausted accounts in sequence consumes 40s+ ($22.6s + 18.0s = 40.6s$), exceeding caller socket timeouts (15s in `advisor_consult`, or client-side 30–45s) and causing `[499] Request aborted`. Do NOT mistake this for "rotation not working" or "all 94 accounts dead" — checking `call_logs` proves healthy accounts deeper in rotation (e.g. `sol-acc-5`, `sol-acc-6`) succeed normally in 13–19s. Verify with `SELECT timestamp, connection_id, model, error_summary, duration FROM call_logs WHERE requested_model LIKE '%chatgpt%' OR model LIKE '%sol%' ORDER BY rowid DESC LIMIT 15;`. Fail fast to Tier 2 (`ag-gemini-pool-3`) within 15–20s to preserve UX responsiveness, and ensure exhausted accounts trigger immediate cooldown exclusion in OmniRoute.
- **Direct 9Router (:20128) Sol High fallback when :20129 stalls or hits web pool limits:** If OmniRoute :20129 is unresponsive, hanging on socket reads, or returning ChatGPT-web pseudo-200 limits on `review`, 9Router on :20128 (`http://192.168.110.123:20128/v1`, model `gpt-5.6-sol` using `NINEROUTER_API_KEY`) is an immediate, fast (<15s) direct fallback route to obtain genuine Sol High judgment without suffering cascading waterfall timeouts across multi-account pools.
- **Probe cap discipline — stop after 3 model failures:** When hunting for a working Advisor route, cap at 3 distinct model attempts. After 3 failures (timeouts, rate limits, ALL_TARGETS_SKIPPED), surface the primary answer with `Advisor: unavailable` label. Do NOT keep probing — it wastes 3+ minutes and the primary answer is already complete.
- **Minh bạch tuyệt đối khi Advisor rớt / Port collision:** Khi cổng :20129 bị chiếm dụng hoặc endpoint review bị timeout/treo, Coordinator BẮT BUỘC phải thông báo trung thực ngay với User rằng Advisor Sol đang offline/unavailable. CẤM TUYỆT ĐỐI im lặng nuốt lỗi, hoặc tự đưa ra nhận định cá nhân rồi để user hiểu lầm là Advisor đang cùng đàm đạo.
- **Phân biệt tiến trình OmniRoute vs Rogue process:** Tiến trình chạy trên cổng 20129 với dòng lệnh `node.exe ... scripts/dev/run-next.mjs start` CHÍNH LÀ OMNIROUTE (Next.js runner), KHÔNG PHẢI tiến trình lạ chiếm cổng. Bằng chứng là Coordinator vẫn chat được bình thường qua `omni-worker` trên chính cổng này. Lỗi timeout của `review` là do upstream web-pool / combo waterfall, không phải do port bị cướp.
- **Kích hoạt tức thì 9Router (:20128) streaming fallback & Backend Architecture:** Khi cổng :20129 treo quá 1 lượt hoặc dính web-pool waterfall, BẮT BUỘC nhảy ngay sang 9Router (:20128) với `model: gpt-5.6-sol`, `stream: true` và `NINEROUTER_API_KEY`:
  * *Bắt buộc SSE Streaming*: 9Router trả về Server-Sent Events (`data: {...}`). BẮT BUỘC gọi với `stream: true` và parse dòng `data: `, tuyệt đối không `json.loads(res.read())` trực tiếp trên toàn bộ response (sẽ crash `Expecting value: line 1 column 1` do định dạng SSE).
  * *Backend thực tế của 9Router `gpt-5.6-sol`*: Combo định nghĩa `cx/gpt-5.6-sol` -> `ag/claude-opus-4-6-thinking`. Khi Codex không có credentials, 9Router tự động fallback sang **Antigravity Claude Opus Thinking** (Google Cloud OAuth). OpenCode DeepSeek Flash hiện tại đang chết (HTTP 400: Upstream request failed).
  * *Minh bạch tuyệt đối*: Nếu cả 2 cổng đều không phản hồi, BẮT BUỘC báo ngay `Advisor: unavailable`, cấm tự phân tích rồi gán ghép như thể Advisor đang trả lời.
- **Testing through a full CLI wrapper only:** wrapper startup/plugin overhead can time out while the dispatcher works. Test the actual dispatcher boundary with a mocked primary response and a mocked Advisor seam, then use a live route probe as separate evidence.
