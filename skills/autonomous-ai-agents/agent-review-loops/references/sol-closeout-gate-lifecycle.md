# Sol Closeout Gate and Dispatch Lifecycle Semantics

Use this reference when operating or updating the Sol closeout state machine, dispatch contract hook, or review verification loops.

## 1. Dispatch Contract Hook Plan-Failure Semantics

When validating SOL plans in `hooks/guard_dispatch_contract.py`:
- Plan failures include:
  1. Missing plan file (`valid_sol_file` not found on disk)
  2. Expired plan (age `time.time() - created_at > 600s`)
  3. Unreadable plan file (corrupted JSON or I/O error)
  4. Missing plan metadata (`created_at` missing or `<= 0`)
- **Required lifecycle emission**:
  - `state`: `REMEDIATION_REQUIRED`
  - `lifecycle`: `REMEDIATION_REQUIRED`
  - `plan_state`: `SOL_PLAN_REQUIRED`
  - Explicit `blocker` and `next_action` describing remediation
- **Rationale**: Plan issues are recoverable through re-running the planner or regenerating a valid plan. Emitting `REMEDIATION_REQUIRED` signals to the coordinator that action is needed while maintaining `plan_state: SOL_PLAN_REQUIRED` for gate tracking.

## 2. Closeout Gate HARD_STOP Boundaries

In `closeout_gate.py` (`run_sol_closeout_state_machine`):
- `HARD_STOP` is **strictly restricted** to:
  1. `safety_failure`: verified safety violation or dangerous operation
  2. `integrity_failure`: audit log hash chain tamper or corruption
  3. `unauthorized_fallback`: unapproved or malformed fallback bypassing planning contracts
- **Generic `nonrecoverable` rule**:
  - A reviewer or verification hook emitting generic `nonrecoverable=True` **must not** trigger `HARD_STOP`.
  - Instead, failed verification or sub-threshold review follows the bounded retry lifecycle:
    - Attempt < max_attempts: emits `REMEDIATION_REQUIRED`
    - Attempt >= max_attempts: emits `REVIEW_REMEDIATION_EXHAUSTED` (recoverable=True, terminal=False)
- Arbitrary nonrecoverable flags without safety, integrity, or unauthorized fallback failures remain recoverable and bounded.

## 3. Sol Web HTTP 413 Payload Ceiling & Truncation Invariants (`sol_payload_guard.py`)

When sending diffs, logs, or prompt contexts to ChatGPT Web upstream (`gpt-web-sol` on OmniRoute `:20129`):
- **Physical Fracture Threshold**: Upstream Nginx/Cloudflare crashes with HTTP 413 at **66,724 Bytes (~65 KiB)**.
- **Payload Guard Thresholds**:
  - `SOL_TARGET_BYTES = 32_768` (32 KiB) target budget.
  - `SOL_HARD_MAX_BYTES = 37_952` Bytes fail-closed ceiling (under absolute 40,000 Bytes cap).
- **Serialization & Encoding Discipline**:
  - Always measure UTF-8 byte length after JSON serialization (`json.dumps(..., ensure_ascii=False).encode('utf-8')`). Never use Python string character length `len(str)`.
  - Always transmit `data=raw_bytes` with `Content-Type: application/json; charset=utf-8` to prevent HTTP clients from escaping UTF-8 characters into `\uXXXX` sequences that cause byte explosion.
- **Smart Truncation Priorities**:
  - **P0 (Never Truncate)**: Rubric, Patch Contract O(1), file stats, git candidate scope.
  - **P1 (Last to Truncate)**: Error logs, Tracebacks, Assertions with $\pm 4$ lines of context. Line-anchoring regex must bound search to the first 4,096 characters per line to eliminate ReDoS.
  - **P2 / P3 (First to Truncate)**: Middle hunks of large diffs and non-error log outputs.
- **Truncation Manifest & Verdict Qualifier**:
  - When diff or logs are truncated (`truncated=True`), `format_manifest()` is injected with the original SHA-256 hash.
  - If a reviewer model returns `APPROVED` on truncated content, the gate must automatically downgrade the verdict to `APPROVED_PARTIAL` and set `ready_to_close: False`.

## 5. Large Diff Closeout Review: Dual-Tier Routing & Auto-Fallback to Claude Opus 4.6 High (`ag-opus`)

When a session introduces large changes (>30 KB diff, e.g. monolithic script creation, large test suites, or multi-module updates):
- **Problem with Default Sol Reviewer (`review` / `gpt-5.6-sol-high`)**:
  - Upstream ChatGPT-web has a physical HTTP 413 ceiling at 66,724 Bytes, enforced by `sol_payload_guard` at 37,952 Bytes (`CALCULATED_MAX_ALLOWED`).
  - Diffs >30 KB are automatically truncated by `digest_diff()`, causing Sol Auditor to see truncated files and deduct points (scoring 78–83/100, citing "diff bị lược bớt một phần").
- **Solution — Dual-Tier Smart Routing in `closeout_gate.py`**:
  - **Normal diffs (≤ 30 KB)**: Default to Sol High (`review` / `chatgpt-web-pool`) on OmniRoute `:20129` for fast, lightweight gate checks.
  - **Large context (> 30 KB)**: Automatically detect byte size at ingress and route directly to **Claude Opus 4.6 Thinking High (`ag-opus`)** on the 85-account Antigravity pool.
  - **Payload Guard Bypass**: When `is_claude_ag` (`"claude"`, `"opus"`, `"sonnet"`), `closeout_gate.py` sets `skip_payload_guard=True`, allowing the full 60 KB–100 KB+ diff and test evidence to reach the model un-truncated.
  - **Multi-tier Auto-Fallback**: If Sol High fails or gets truncated, auto-fallback sequentially to `ag-opus` → `ag-sonnet`.
- **Direct CLI Execution for Large Diffs**:
  - For known large diffs (>500 lines or >30 KB), invoke directly:
    `python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD~1 --model ag-opus --json-output`

## 6. Hard Invariant: Closeout Completion & Anti-Premature "Done" Gate

- **Never declare "xong xuôi trọn vẹn" without Gate Exit Code 0**:
  - The coordinator is strictly forbidden from claiming the task or session is finished, done, or wrapped up when `closeout_gate.py` returned exit code != 0 or overall score < 85.
  - Doing so violates the highest-precedence HARD INVARIANT.
  - If a user sends a single period (`.`) or asks about progress after a gate failure, it is a stern signal that the coordinator hallucinated completion or lost context. Check git diff and re-run gate immediately until `APPROVED` (≥ 85/100) and `ready_to_close: true` are achieved.

## 7. Worker Fix-Up Remediation Patterns for Sol Auditor Scorecard (>= 85 Threshold)

When a worker agent receives a remediation contract after Sol Reviewer scores in the 80–84 range:
- **Avoid Pure String-Search Tests**: Sol Auditor penalizes tests that only check static file contents (`read_text().find(...)` / ordering). Pair static regression checks with a behavioral runtime unit test using mocks (`MagicMock` for `page.locator`, `page.evaluate`, etc.) to demonstrate functional mechanics.
- **Anchor String-Ordering Invariants to Callsites, Not Definitions**: When using `assertLess(idx_first, idx_second)` to verify operational order (e.g. `tel_input.fill` before `enforce_sms_channel`), never search for tokens like `sms_label = ...` that exist inside helper function definitions earlier in the file. Always search for the exact callsite invocation in the execution flow.
- **Explicit State Confirmation over Fire-and-Forget**: When enforcing UI state (e.g. radio buttons, checkboxes, dropdowns), query back the actual DOM state (e.g. `smsRadio.checked`) and feed `confirmed: bool` into telemetry payloads. Sol Auditor routinely docks `Logic Correctness` and `Code Architecture` when operations execute without verifying the post-action DOM state.
- **Enriched Observability Context**: Ensure telemetry events capture outcome flags (e.g. `{"confirmed": True, "attempt": ...}`) to satisfy Sol's `Telemetry & Obs` rubric.
- **Clean Diff Scope (Isolate Multi-File Cross-Script Noise)**: When fixing a core issue (e.g. supervisor scheduler), avoid bundling speculative changes in sibling consumer scripts unless strictly required. Sol Auditor deducts points on `Logic Correctness` (citing integration boundary risks between the two scripts) and `Test Evidence` (demanding comprehensive end-to-end integration evidence for both scripts). Keeping the candidate diff atomic and targeted to the primary file plus its dedicated test suite ensures a focused evaluation.
- **Three Pillar Test Suite to Break the 84-point Glass Ceiling**:
  1. *Scale Simulation Test*: Simulate a 50-100 account dataset to prove scheduling invariants (FIFO least-recently-attempted, distinct proxy ports, and anti-starvation cooldown) hold at production farm scale.
  2. *Multi-Stage State Transition Regression*: Explicitly mock and test non-target pipeline stages (e.g. `HOTMAIL_LOGIN` $\to$ `CODEX_OAUTH`, `WAIT_7D` $\to$ `CHANGE_INFO`) to prove changes to shared executors/schedulers cause zero regressions across the broader lifecycle.
  3. *Failure Rollback & Exception Safety*: Mock runtime exceptions in external dependencies (e.g. GPM API timeouts) and assert that the system fails gracefully with clean error reporting without corrupting or partially updating state variables (`status`, `chatgpt_registered_at`, `codex_oauth_at`).
- **Structured Telemetry Invariants (`log_telemetry_event`)**: Implement structured dictionary logs with ISO UTC timestamp, explicit event names (e.g. `stage_execution_result`, `scheduler_cooldown_skip`), and subsystem identifiers (`subsystem: gpm_supervisor`) to reliably score $\ge 13/15$ on Telemetry & Observability.
- **Reviewer Model Timeout Guard**: When using `--model ag-opus-pool`, high server load can cause 300s read timeouts. Prefer default `review` or `chatgpt-web/gpt-5.6-sol-high` for standard diffs $\le 30$ KB, where execution completes reliably in 30-60s.
- **Base Ref Selection & Untracked/Monolithic File Contamination**: When invoking `closeout_gate.py`, `--base` must refer strictly to the commit immediately before the targeted fix. If `--base` spans a commit that added a new monolithic script (>800 lines), the extracted diff explodes (>50KB), triggering `sol_payload_guard` truncation and leading Sol Auditor to reject with `NEED_CONTEXT: <file>(partial)` and low scores (~76/100).
- **Staged Repo Mode vs Raw `--input` File Mode**:
  - Tuyệt đối TRÁNH xuất diff thô nhiều file rồi gọi `--input <patch_file>`. Ở chế độ `--input`, `closeout_gate.py` coi toàn bộ file là plain text và đưa qua `focus_log` cắt xén payload, dẫn đến việc mất test evidence và reviewer trừ điểm/reject (68-83đ) với nhận xét: *"Phần review bị giới hạn vì input là diff/log đã bị cắt... không có đầy đủ test run output"*.
  - **Golden Path**: Stage đúng các file source + test đã sửa bằng `git add <file1> <file2>`, sau đó gọi:
    `python D:/Taadaa/tools/closeout_gate.py --repo <path> --json-output`
    Ở chế độ `--repo` có staged changes, `closeout_gate` tự động bind SHA256 audit binding, trích xuất focused tests tương ứng từ staged files, chạy pytest thực tế đưa test log vào payload, và phân bổ ngân sách byte chuẩn giữa diff và test evidence mà không bị cắt cụt.
- **Coordinator Anti-Pattern — Cấm Hỏi Lại Khi Đã Nhận Lệnh Thực Thi ("Sửa đi" -> Cấm xin phép lần 2)**:
  - Khi user đã phát lệnh rõ ràng `"Sửa đi gọi sol tư vấn"`, coordinator tham vấn Sol xong BẮT BUỘC bắt tay vào thực thi ngay lập tức.
  - Tuyệt đối CẤM dừng lại hỏi: *"Sếp duyệt bản vẽ này thì em bắt đầu làm..."*. Việc hỏi lại sau khi đã có lệnh thực thi bị coi là trốn việc/đóng băng, kích hoạt phản ứng tiêu cực (`"????"`) từ user.


## 4. Closeout Gate Anti-Freeze, Hostname Security & Rubric Validation Invariants

To avoid subagent 600s freezes and ensure tamper-resistant reviews in `closeout_gate.py`:
- **Global Pipeline Deadline**:
  - Establish a strict `global_deadline = time.monotonic() + 540.0` at pipeline kickoff (`main()`).
  - Pass the remaining deadline down to test runners and HTTP client retries (`timeout=(5.0, min(timeout, remaining))`).
  - Subprocess git commands must enforce `timeout=30s` to prevent OS/lock freezes.
- **Fail-Closed HTTP & Retry Semantics**:
  - Do NOT retry on `requests.exceptions.ReadTimeout` or HTTP client error `4xx` (e.g. 400, 413).
  - Do NOT retry when server returns HTTP 200 with non-JSON body (`ValueError` thrown immediately).
  - If `global_deadline - time.monotonic() < 60s` before git steps or review, abort immediately with exit code 1.
- **Strict Hostname & Scheme Validation**:
  - Hostname must be parsed via `urllib.parse.urlsplit(url).hostname` and match strictly against trusted hosts (`localhost`, `127.0.0.1`, `192.168.110.123`).
  - Scheme must be `http` or `https`. Reject userinfo (`username`/`password`) to prevent URL spoofing tricks (e.g., `localhost.attacker.com`, `127.0.0.1@evil.com`).
  - Apply the check to CLI arguments (`--base-url`) and environment variables (`OMNI_ROUTE_URL`, `OMNI_URL`).
- **Scorecard Rubric Schema Enforcement**:
  - `ready_to_close` must be strict boolean `True` (reject truthy strings like `"false"` or integers).
  - Scorecard must contain all required rubric criteria (`set(bd) == set(RUBRIC_MAX_LIMITS)`), with no extraneous keys, negative scores, or scores exceeding category ceilings.
  - Calculated total from breakdown must match `overall_score` within 1 point (`abs(total - calc_total) <= 1`); otherwise emit `REJECTED`.
  - In `--repo` mode, passing `--skip-test` triggers an immediate fail-closed exit code 1 (`TEST_SKIPPED`) without invoking costly AI review.

