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

## 5. Large Diff Closeout Review: Auto-Fallback to Claude AG Sonnet (`ag-sonnet`)

When a session introduces large changes (>38 KB diff, e.g. monolithic script creation, large test suites, or multi-module updates):
- **Problem with Default Sol Reviewer (`review` / `gpt-5.6-sol-high`)**:
  - Upstream ChatGPT-web has a physical HTTP 413 ceiling at 66,724 Bytes, enforced by `sol_payload_guard` at 37,952 Bytes (`CALCULATED_MAX_ALLOWED`).
  - Diffs >38 KB are automatically truncated by `digest_diff()`, causing Sol Auditor to see truncated files and deduct points (scoring 78–83/100, citing "diff bị lược bớt một phần").
- **Solution — Claude AG (`ag-sonnet` / `ag-opus-pool`) on OmniRoute (:20129)**:
  - Claude Sonnet 4.6 (backed by 114-account pool on OmniRoute) has a 200,000-token context window and does not route through ChatGPT-web web-scraping interfaces.
  - In `closeout_gate.py`, `is_claude_ag` (`"claude" in model or "sonnet" in model or "opus" in model`) bypasses `sol_payload_guard` (`skip_payload_guard=True`), sending the full 60 KB–100 KB+ diff and test evidence intact.
- **Auto-Fallback Mechanism**:
  - In `run_gate_pipeline()`, if the default `review` model fails (verdict != APPROVED or score < 85) and diff was truncated, `closeout_gate.py` automatically falls back to `ag-sonnet` to perform a full-context evaluation without truncation.
- **Direct CLI Execution**:
  - For known large diffs (>500 lines or >38 KB), invoke directly:
    `python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD~1 --model ag-sonnet --json-output`

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

