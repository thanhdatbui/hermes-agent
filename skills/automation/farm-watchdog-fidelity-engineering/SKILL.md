---
name: farm-watchdog-fidelity-engineering
description: "Use when designing or fixing watchdogs and cron reports."
---

# Farm Watchdog & Reporting Fidelity Engineering

## 1. When to Use
Use when creating, auditing, modifying, or troubleshooting background watchdogs, scheduled cron reports, and alert aggregators on automation farms.
Applies whenever reports fail to reflect actual fleet health, mask dropped machines, report false aggregate metrics, or omit actionable failure details.

---

## 2. Core Invariants (Zero Reporting Blindspots)

### Invariant 1: Anti-Phantom Fleet Health (Offline Device Isolation)
- **Anti-Pattern:** Iterating over `get_connected_devices()` alone. If devices drop USB, crash, or lose power, they vanish from the connected list, producing a false "100% success on online devices" report while hardware outages go unnoticed.
- **Rule:** Always diff the canonical fleet from the source of truth (Workbook, Excel master, or Fleet DB) against active connections:
  ```python
  fleet_machines = load_machine_serials(cluster)  # Canonical list
  online_fleet = [m for m, s in fleet_machines if s in connected]
  offline_fleet = [m for m, s in fleet_machines if s not in connected]
  ```
- **Reporting Contract:** If `offline_fleet` is non-empty, explicitly display:
  `• Mất kết nối ADB (OFFLINE): N máy (M01, M02) - Cần cắm lại cáp / kiểm tra hub`

### Invariant 2: Direct State Over Key Desync (Daily Counter Reliability)
- **Anti-Pattern:** Relying solely on top-level session aggregator keys like `state["_daily_stats"]["count"]`. In multi-worker or concurrent processes, this key can desync, reset to 0, or fail to persist, causing reports to show "0/30" despite full execution.
- **Rule:** Always implement direct fallback calculation across individual entity records using timestamp comparison:
  ```python
  def count_nurtured_today(state: dict, now_ts: float) -> int:
      today = datetime.fromtimestamp(now_ts).date()
      return sum(
          1 for k, v in state.items()
          if not k.startswith("_") and isinstance(v, dict)
          and v.get("last_nurtured")
          and datetime.fromtimestamp(v["last_nurtured"]).date() == today
      )
  ```

### Invariant 3: Anti-Fake-Soaking (Session Loss Discrimination)
- **Anti-Pattern:** Treating all non-completed accounts as "soaking / warming up" (`status != 'success' -> soaking += 1`). Accounts with `status == 'NEEDS_LOGIN'` (expired cookies, session lost) are dead and cannot soak.
- **Rule:** Explicitly separate `NEEDS_LOGIN` accounts from legitimate soaking profiles. Surface the exact emails so operators can trigger re-login workflows:
  ```text
  • Đang ngâm (chờ phiên nuôi): 1
  • Sẵn sàng bật 2FA: 16
  ⚠️ Acc văng cookie (NEEDS_LOGIN): 4 profile
    - user1@gmail.com
    - user2@gmail.com
  ```

### Invariant 4: Actionable Failure Identity over Aggregate Counters
- **Anti-Pattern:** Emitting generic counters like `✗ 7 failed` or `Errors: 5` without identifying which machines or accounts failed.
- **Rule:** Store and surface structured `failed_details` arrays containing:
  - Identity handle: Machine ID, Slot, or Account email.
  - Failure taxonomy: `PLATFORM` (transport, crash, timeout) vs `SCRIPT` (wrong credentials, checkpoint, captcha).
  - Truncated reason string ($\le 60$ characters).

### Invariant 5: Anti-Silent Expiry (End-of-Window Forced Flush)
- **Anti-Pattern:** Suppressing reports when `has_retries_left` is true. If retries remain incomplete when the shift window ends, the watchdog exits silently and the operator receives no report for that entire shift.
- **Rule:** Enforce a hard boundary flush at the end of the shift schedule (e.g. at minute 45 of the final hour):
  ```python
  if (now_hour == 4 and datetime.now().minute >= 45) or now_hour >= 5:
      should_report = True
  ```

### Invariant 6: Exception-Driven Alerting (Silent on Nominal, Loud on Anomaly)
- **Anti-Pattern:** Emitting verbose periodic status messages on Telegram every 6h even when 100% of accounts and machines are healthy, leading to notification fatigue and ignoring alerts.
- **Rule:** Silence is only valid with positive proof of health. Any empty source, crash, or threshold failure must fail-closed into an alert immediately. Use the `CronRun` pattern from `references/exception-driven-alerting-and-24h-heartbeat.md`.

### Invariant 7: Independent 24H Heartbeat (Dead-Man's Switch at 09:00 VN)
- **Anti-Pattern:** Assuming that silence across a 24h window means nominal health, while a crashed scheduler, corrupted python environment, or severed Telegram webhook went undetected.
- **Rule:** Deploy a separate, lightweight aggregator (`cron_heartbeat.py`) that reads watchdog state files independently and emits exactly 1 digest message daily at 09:00 VN (02:00 UTC) summarizing fleet monitoring vitality.

### Invariant 8: Shift Overrun & Cross-Window Execution Attribution
- **Anti-Pattern:** Batch jobs (e.g., overnight `run_parallel.ps1`) encountering cumulative timeouts, cooldowns, or platform verification blocks (e.g. Google `phone_verify`) across devices, drifting hours beyond their schedule and firing a "BAN ĐÊM" alert during daytime (e.g., 10:00 AM) without execution context.
- **Rule:**
  1. **Shift Hard Time-Fence:** Overnight batch runners should check shift boundary cutoffs (e.g., aborting queued retries once daytime operations begin at 06:00/07:00).
  2. **Execution Window Attribution:** Batch aggregators firing after shift end MUST include execution start time and elapsed duration (e.g. `[Ca Đêm: 02:30 -> 09:55 | Thời gian chạy: 7h25m]`), making the delay immediately obvious to operators.

### Invariant 9: Dynamic Shift Labeling vs Static Header Desync
- **Anti-Pattern:** Assuming that a daytime alert (e.g. at 10:00 AM) titled "BAN ĐÊM" is necessarily a delayed overnight run, when in fact it was a fresh off-cycle batch launched at 10:18 AM with hardcoded report headers. Static/hardcoded shift titles in runner templates decouple alert headers from actual wall-clock execution time.
- **Rule:**
  1. **Dynamic Shift Name Resolution:** Aggregators and report dispatchers must dynamically compute the shift name from execution timestamp (`created_at` / `now_hour`) rather than static template strings.
  2. **Timestamp Verification in Diagnosis:** When diagnosing unexpected alert timing, always check the exact batch directory timestamp (`logs_parallel_YYYYMMDD_HHMMSS`) and `summary.json["created_at"]` first to distinguish between actual execution duration vs off-cycle fresh triggers.
  3. **Batch Cooldown Conformance:** Verify batch size limits (e.g. canonical `maxMachines = 15` after 4-5 day cooldown per device) in summary metadata to confirm selection contract adherence.

### Invariant 10: Cross-Host Multi-Cluster Telemetry Parity (Anti-Silent Cluster Dropping)
- **Anti-Pattern:** A multi-cluster orchestrator or watchdog (e.g. `cron_night_tiktok_2fa_watchdog.py`) is intended to run across both local (Kibe M01-M80) and remote (Admin M201-M280) clusters, but repeatedly fails to execute or report the remote fleet:
  1. **Path & Shell Assumption Desync:** Hardcoding local controller paths (e.g. leaking `C:\Users\Kibe\...` into remote `$env:GMAIL_REG_PYTHON_EXE` under user `Admin`), or passing POSIX forward slashes (`Set-Location 'D:/Taadaa/...'`) over SSH which causes Windows PowerShell `Test-Path` to return False (exit code 1).
  2. **Inventory Partition Blindspot:** Relying on a single local workbook (e.g. `taikhoan_run_safe.xlsx` with only M01-M80) while the remote fleet resides in a separate workbook (e.g. `admin/PROXYgandienthoai.xlsx`), causing the selection script to evaluate an empty set for the remote cluster.
  3. **Unilateral Local Log Scraping:** Aggregator functions (`read_summary_json`) only scanning local runtime directories (e.g. `D:/CodexRuntime/...`), silently defaulting remote cluster statistics to 0 without verifying or fetching the remote host's output summary.
  4. **Resource Assignment Manifest & Lock Root Mismatch:** Launcher scripts requiring explicit `AssignmentManifest` fail closed on remote nodes if the manifest file is missing or only enumerates local machines (`machine:1..80`). Hardcoding `$lockRoot` to `C:\Users\Kibe\.codex\device-locks` also fails on remote nodes where the user is `Admin`.
  5. **Non-Interactive SSH `PYTHONPATH` Deficit:** Child processes launched over non-interactive SSH sessions fail with `ModuleNotFoundError: No module named 'automation_core'` because controller shell exports are not inherited.
- **Rule:**
  1. **Explicit Cluster Runtime Contracts:** Pass cluster-specific Python executables, repo roots, workbooks, and manifests configured per cluster (e.g. `admin.yaml` vs `kibe.yaml`). Use `$env:USERPROFILE\.codex\device-locks` for multi-user path portability.
  2. **Self-Bootstrapping PYTHONPATH:** Launchers (`run_all.ps1`) must self-bootstrap sibling source paths (`automation-core\src`) into `$env:PYTHONPATH` if absent.
  3. **Strict Dual Telemetry Requirement:** Watchdogs dispatching to remote hosts via SSH must parse structured JSON or standard stdout telemetry (`TOTAL=N SUCCESS=N PHONE_VERIFY=N ...`) emitted on stdout and merge breakdowns across clusters before reporting.
  4. **Zero-Count Remote Alert:** If a cluster configured for batch execution returns 0 machines selected, 0 success, and 0 failed, the watchdog must flag this anomaly (`⚠️ Cluster Admin: Không thu thập được telemetry / 0 máy được chọn`) rather than silently suppressing the missing cluster. See `references/cross-cluster-multi-host-watchdog-parity.md`.

### Invariant 11: Batch Watchdog Idempotency vs Partial-Failure Storm (Anti-Spam & Execution Decoupling)
- **Anti-Pattern:** Conflating run completion with 100% success (`already_ran_today = is_success is True` or `lane_status == 'success'`). On physical device farms (~160 phones), partial failures (SIM dropped, Google `phone_verify`, carrier rate-limits) are normal operating occurrences. When a 15-minute cron watchdog treats any `partial_failure` as "never executed today", it immediately relaunches the multi-hour batch after releasing device locks, flooding Telegram channels with repetitive reports (e.g. 00:38, 02:34, 03:23, 10:32, 11:17) and trapping farm devices in an infinite rerun loop that starves other scheduled shifts.
- **Rule:**
  1. **Decouple Execution State from Zero-Failure Outcome:** `already_ran_today(today_str)` must check if the shift batch has executed for the target day (`last_date == today_str` or `last_run_at.startswith(today_str)`), regardless of whether status is `success` or `partial_failure`.
  2. **Strict Manual / Scoped Rerun Contract:** Never allow unattended crons to loop on partial failures. Re-running failed batches requires an explicit `--force` flag or a scoped, targeted remediation task.
  3. **Universal Day/Night Chain Parity:** Apply this rule uniformly across all multi-phase batch watchdogs (`cron_night_tiktok_2fa_watchdog.py`, `post_noon_chain_watchdog.py`, `post_morning_gmail_2fa_watchdog.py`). See `references/batch-watchdog-idempotency-and-anti-spam-storm.md`.

### Invariant 12: Fast-Filter File-Scan Pre-Check (Anti-Timeout on Large Runtime/Idempotency Directories)
- **Anti-Pattern:** Iterating with `pathlib.Path.glob("*.json")` and reading/parsing every file (`read_text()` + `json.loads()`) in directories containing thousands of files (e.g. `idempotency/post-attempts` with >9k receipts). On Windows NTFS under cold-cache conditions, reading 9,000+ files sequentially exceeds 60s, triggering cron timeouts (exit 124) and preventing watchdogs from ever completing.
- **Rule:**
  1. **Stat-First Pre-Filtering:** Use `os.scandir()` and filter by `entry.stat().st_mtime` BEFORE opening or reading file content. If searching for stale records older than $N$ hours, immediately skip files where `now - st_mtime < min_age_seconds` without touching file contents.
  2. **Iterative Batch Processing:** When parsing content is required across large sets, avoid full-directory synchronous loads in short-timeout (<60s) cron scripts or ensure the timeout budget accommodates NTFS cold-cache traversal. See `references/watchdog-timeout-and-file-scan-bottleneck.md`.

### Invariant 13: ADB Host Unreachability vs Zero-Device Fleet Discrimination & Deferred Daily Closeout
- **Anti-Pattern:** Treating an unreachable ADB host (e.g. remote daemon restarting, socket timeout, port 5037 dead) identically to an reachable host with 0 online devices (`connected = {}`). The script reports "0 completed, 0 error" instead of a connection failure alert. Furthermore, prematurely committing `reported_date = today_str` locks out future retry intervals in the same shift window after the host daemon recovers.
- **Rule:**
  1. **Cluster Reachability Tracking (`reachable = False` before call):** Verify subprocess exit code and timeout explicitly. If `adb devices` fails/times out, flag `cluster["reachable"] = False`.
  2. **Unreachable Cluster Warning Contract:** Report `⚠️ Cluster không kết nối được ADB; không thể xác nhận trạng thái máy.` instead of aggregate 0s.
  3. **Deferred Daily Reporting Closeout:** Only commit `reported_date = today_str` when all configured clusters are reachable (or explicit `--force` override), allowing subsequent ticks to clear cache or reconcile once ADB daemon recovers. See `references/adb-host-unreachability-and-deferred-closeout.md`.

### Invariant 13: Mock Test Signature Sanitization, Local-to-UTC Normalization, and Three-Way Sync Parity
- **Anti-Pattern:**
  1. A compliance watchdog audits logs using generic regex (`pytest`, `target.py`), failing to match real test assertion payloads (`Review then apply...`, `grep -rn foo...`, `audit_test...`). Over 70% of reported violations are synthetic test mock artifacts.
  2. The watchdog parses naive timestamps from files using `datetime.now().isoformat()` with `.replace(tzinfo=timezone.utc)`, distorting the 6-hour rolling window by 7 hours and pulling in historical incidents from 13 hours prior.
  3. The agent edits scripts in the repo worktree but forgets that Hermes cron runs standalone scripts from `%LOCALAPPDATA%\hermes\scripts\`, resulting in stale runtime execution.
- **Rule:**
  1. **Comprehensive Test Signature Sanitization:** Maintain an explicit `TEST_MOCK_SIGNATURES` tuple containing known test payloads and filter them out via `is_test_log_line(line)`.
  2. **Designated Naive Normalization:** Map files with naive local timestamps (`LOCAL_NAIVE_LOGS = {"dispatch_audit.jsonl", "console_block_audit.jsonl"}`) and convert them from host local time to UTC before window cutoff evaluation.
  3. **Three-Way Sync Parity:** Synchronize script changes across (1) `D:/Taadaa/tools/`, (2) `deploy/hermes-home/scripts/`, and (3) `%LOCALAPPDATA%\hermes\scripts\` via `cron_sync_watchdog.py --force`.
  4. **Gateway Restart Discrimination:** `no_agent: true` cronjobs spawn fresh Python processes from disk per tick and NEVER require Gateway restart. Gateway restart is strictly reserved for in-memory core engine modules (`conversation_loop.py`, `coding_context.py`). See `references/compliance-watchdog-mock-sanitization-and-three-way-sync.md`.

### Invariant 14: Downstream Schema Semantics & False-Negative Flagging (Empty Field vs Missing Account)
- **Anti-Pattern:** A reporting watchdog or lifecycle supervisor validates entity readiness using compound credential assertions (e.g. `bool(username and password)`) for external platforms (e.g. TikTok, ChatGPT) when upstream registration flows intentionally leave optional or unprompted credentials empty (e.g., TikTok email/OTP reg flow leaves TikTok password empty in tracking to prevent fake passwords). This misclassifies valid active accounts as "missing info" or "unregistered" (e.g., reporting 225 matured `WAIT_7D` accounts as "Thiếu thông tin TikTok"), stalling the lifecycle pipeline indefinitely.
- **Rule:**
  1. **Primary Identifier Validation:** Validate platform presence by the primary canonical identifier (e.g., `bool(username)` for TikTok ID), not compound credential bundles, unless the downstream action specifically consumes the secondary credential.
  2. **Cross-Check with Execution Source of Truth:** Before reporting accounts as "missing registration" or "lacking platform data", cross-check against the execution source of truth (e.g., `taikhoan_run_safe.xlsx` currently dispatching feed/video runs) rather than relying solely on optional credential columns in static workbooks.
  3. **Non-Zero Exit Code on Target Missing:** If a security or lifecycle runner is invoked for a specific entity (`--email <target>`) but finds no matching rows in the master workbook, it MUST exit with a non-zero code (`return 1`). Exiting with 0 when target accounts are skipped causes callers (supervisors) to mistake a no-op for a successful completion, producing false "DONE" status transitions.

### Invariant 15: Phantom State Advancement & Registration CLI Returncode Trap
- **Anti-Pattern:** A child registration script (`chatgpt_gpm_direct_reg.py`) returns exit code `0` when no matching candidate is found in workbooks or when registration encounters fatal errors (`FAIL_PASSWORD_NOT_FOUND`, `FAIL_OTP_TIMEOUT`). The parent supervisor (`batch_gpm_5profiles_supervisor.py`) evaluates `proc.returncode == 0` as complete registration, immediately stamps `chatgpt_registered_at = now()`, and advances hundreds of accounts through a 7-day soak and password change cycle to `DONE` without ever opening a browser.
- **Rule:**
  1. **Strict Non-Zero Failure Contract:** The registration runner MUST return `1` on any failure or when target `--email` has no candidate. Return `0` strictly when `status in ("SUCCESS", "ALREADY_LOGGED_IN", "DRY_RUN_OK")`.
  2. **Cross-Cluster Workbook Path Resolution:** Candidate lookups must parse all active cluster workbooks (`admin/` and `kibe/`), with safe fallback (`normalize_password(cred["pwd"])`) if optional password columns (`PASS CHATGPT`) are absent.
  3. **UI State Discrimination:** Never confuse `/about-you` ("Bạn bao nhiêu tuổi?") with an expired session challenge. The "About You" screen proves the account was NEVER registered on OpenAI; an existing registered account exclusively prompts for OTP at `/email-verification`.
  4. **OTP Subject Matching:** OpenAI OTP email subjects vary by locale ("Your temporary ChatGPT verification code" vs "Mã xác minh tạm thời của bạn cho ChatGPT"). Never filter solely on `"openai"` in subject line — check both `"openai"` and `"chatgpt"` across combined subject and sender address. See `references/phantom-chatgpt-registration-and-exit-code-fidelity.md`.

---

## 3. Verification Protocol for Watchdogs & Reports
1. **Syntax & Compilation:** Run `python -m py_compile <script.py>`.
2. **Deterministic Telemetry Test:** Run focused pytest verifying AST structure, telemetry output to stderr, and empty-input edge cases.
3. **Dry-Run / Live Probe:** Execute with `--dry-run` or direct execution ensuring stdout contains only formatted report text while metrics route to stderr.
4. **OneDrive & Deployment Parity:** Always sync updates between repo deployment path (`deploy/hermes-home/scripts/`) and shared operational directory (`OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`).

---

## 4. References & Case Studies
- [`references/adb-host-unreachability-and-deferred-closeout.md`](references/adb-host-unreachability-and-deferred-closeout.md) — Case study: ADB host unreachability vs zero-device fleet discrimination, misleading zero-error reports, and deferred daily closeout.
- [`references/batch-watchdog-idempotency-and-anti-spam-storm.md`](references/batch-watchdog-idempotency-and-anti-spam-storm.md) — Case study: Decoupled idempotency contract preventing partial-failure rerun loops and Telegram spam storms.
- [`references/cross-cluster-multi-host-watchdog-parity.md`](references/cross-cluster-multi-host-watchdog-parity.md) — Root causes and contracts for cross-host watchdog execution and telemetry collection (Kibe local vs Admin remote).
- [`references/exception-driven-alerting-and-24h-heartbeat.md`](references/exception-driven-alerting-and-24h-heartbeat.md) — Exception-driven alerting, fail-closed tri-state model, and the 24h heartbeat aggregator (Dead-Man's Switch).
- [`references/phantom-chatgpt-registration-and-exit-code-fidelity.md`](references/phantom-chatgpt-registration-and-exit-code-fidelity.md) — Case study: Phantom ChatGPT registration, CLI returncode traps, and OpenAI onboarding UI discrimination.
- [`references/gateway-agent-max-turns-budget-and-refund-bug.md`](../../hermes/hermes-gateway-ops/references/gateway-agent-max-turns-budget-and-refund-bug.md) — Xử lý trần 20 tool iterations bóp nghẹt watchdog/coordinator và bug refund() conversation_loop.
- [`references/zero-reporting-blindspots-and-watchdog-fidelity.md`](references/zero-reporting-blindspots-and-watchdog-fidelity.md) — Case study: Eliminating blindspots in Taadaa Farm cron reports (ADB offline isolation, state desync fallback, NEEDS_LOGIN separation, starving slot alerts).
- [`references/watchdog-timeout-and-file-scan-bottleneck.md`](references/watchdog-timeout-and-file-scan-bottleneck.md) — Case study: Watchdog timeout & file-scan bottleneck in large idempotency directories (>9k files).
