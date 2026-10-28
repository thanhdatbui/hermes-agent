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
  6. **`Write-Host` Telemetry Swallowing & Monolithic Reporting Mask:** Using `Write-Host` in nested PowerShell scripts over SSH traps output in the Information Stream instead of Stdout, causing regex parsers (`TOTAL=N`) to find empty telemetry. When combined with a single monolithic report template (`[TOÀN FARM]` without per-cluster breakdown), the report silently displays only local numbers (e.g. 15 machines), misleading operators into believing the remote fleet never ran.
- **Rule:**
  1. **Explicit Cluster Runtime Contracts:** Pass cluster-specific Python executables, repo roots, workbooks, and manifests configured per cluster (e.g. `admin.yaml` vs `kibe.yaml`). Use `$env:USERPROFILE\.codex\device-locks` for multi-user path portability.
  2. **Self-Bootstrapping PYTHONPATH:** Launchers (`run_all.ps1`) must self-bootstrap sibling source paths (`automation-core\src`) into `$env:PYTHONPATH` if absent.
  3. **Strict Dual Telemetry Requirement:** Watchdogs dispatching to remote hosts via SSH must parse structured JSON or standard stdout telemetry emitted on stdout (`Write-Output`, not `Write-Host`) and merge breakdowns across clusters before reporting.
  4. **Mandatory Per-Cluster Breakdown Lines in Multi-Cluster Reports:** Multi-cluster batch watchdogs MUST ALWAYS display split lines (e.g. `• Farm Kibe (M01-M80): ...` and `• Farm Admin (M201-M280): ...`). Never lump all numbers into a single aggregate when multiple nodes participate. If a remote cluster yields 0, explicitly flag `⚠️ Cluster Admin: 0 máy / chưa nhận telemetry`.
  5. **Coordinator Remote Probe Bridge:** Coordinator terminal commands cannot run raw `ssh` due to allowlist guards; use `python D:/Taadaa/tools/admin_ssh.py --powershell "<cmd>"` (with allowed prefixes: `Get-`, `Set-`, `python`, etc.) for remote diagnosis. See `references/cross-cluster-multi-host-watchdog-parity.md`.

### Invariant 11: Batch Watchdog Idempotency vs Partial-Failure Storm (Anti-Spam & Execution Decoupling)
- **Anti-Pattern:** Conflating run completion with 100% success (`already_ran_today = is_success is True` or `lane_status == 'success'`). On physical device farms (~160 phones), partial failures (SIM dropped, Google `phone_verify`, carrier rate-limits) are normal operating occurrences. When a 15-minute cron watchdog treats any `partial_failure` as "never executed today", it immediately relaunches the multi-hour batch after releasing device locks, flooding Telegram channels with repetitive reports (e.g. 00:38, 02:34, 03:23, 10:32, 11:17) and trapping farm devices in an infinite rerun loop that starves other scheduled shifts.
- **Rule:**
  1. **Decouple Execution State from Zero-Failure Outcome:** `already_ran_today(today_str)` must check if the shift batch has executed for the target day (`last_date == today_str` or `last_run_at.startswith(today_str)`), regardless of whether status is `success` or `partial_failure`.
  2. **Strict Manual / Scoped Rerun Contract:** Never allow unattended crons to loop on partial failures. Re-running failed batches requires an explicit `--force` flag or a scoped, targeted remediation task.
  3. **Universal Day/Night Chain Parity:** Apply this rule uniformly across all multi-phase batch watchdogs (`cron_night_tiktok_2fa_watchdog.py`, `post_noon_chain_watchdog.py`, `post_morning_gmail_2fa_watchdog.py`). See `references/batch-watchdog-idempotency-and-anti-spam-storm.md`.

### Invariant 12: Fast-Filter File-Scan Pre-Check & Runtime Ledger Coupling Safety
- **Anti-Pattern:** 
  1. Iterating with `pathlib.Path.glob("*.json")` and reading/parsing every file (`read_text()` + `json.loads()`) in directories containing thousands of files (e.g. `idempotency/post-attempts` with >9.6k receipts). On Windows NTFS under cold-cache conditions (especially during heavy farm video render/download load), reading 9,000+ files sequentially exceeds 120s, triggering cron subprocess timeouts (`subprocess.TimeoutExpired`) and preventing watchdogs from completing.
  2. **Scope Coupling Trap (Cấm tự ý di dời file runtime):** Agent thấy thư mục có 9.600+ file vội đề xuất di dời toàn bộ file `completed` sang `archived_completed/` mà không tra cứu callers. Thư mục này là ledger chống đăng trùng video (`COMPAT-POST-VERIFY-004`) của `state_machine.py` (`_find_completed_post_receipts_for_machine`). Nếu archive mù quáng, runtime sẽ mất lịch sử đăng và đăng trùng video ngay lập tức.
- **Rule:**
  1. **Stat-First Pre-Filtering:** Use `os.scandir()` and filter by `entry.stat().st_mtime` BEFORE opening or reading file content. If searching for stale records older than $N$ hours, immediately skip files where `now - st_mtime < min_age_seconds` without touching file contents.
  2. **Caller Coupling Verification Before Archival:** Never propose moving, archiving, or purging production data directories without running `git grep` across all dependent workflow repositories (`Tiktok-video`, `automation-core`) to confirm downstream idempotency constraints.
  3. **Progressive Warm-Up Remediation:** When a production canonical script lacks stat pre-filtering during a live run and cannot be modified on the fly, run chunked slice warm-ups (`files[i:i+1000]`) to progressively prime the Windows file system cache into RAM without triggering tool failure loops, then execute the canonical script. See `references/watchdog-timeout-and-file-scan-bottleneck.md`.

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

### Invariant 16: Two-Way Cron Sync Reverse Overwrite Trap & Force-Sync Authority
- **Anti-Pattern:** A watchdog script is fixed and committed to git deploy, but runtime/OneDrive directories hold an older copy with a newer mtime (e.g. from cloud touch/sync). Two-way sync watchdog (`cron_sync_watchdog.py`) skips updating runtime because `dst_mtime > src_mtime` (even with `--force` due to an early return in `sync_file`), then the reverse sync loop sees runtime's newer timestamp and copies the old buggy script back over git deploy, dirty-reverting the commit in the working tree.
- **Rule:**
  1. **Force Flag Authority:** In `sync_file()`, `force=True` must bypass the `dst_mtime > src_mtime` skip guard so deploy always wins when explicitly forced.
  2. **Post-Fix Git Cleanliness Verification:** After editing any cron watchdog, always run `cron_sync_watchdog.py --force` and verify `git status` remains clean.
  3. **Diff Salvage Discipline:** If a watchdog bug recurs after a reported fix, immediately inspect `git diff deploy/hermes-home/scripts/<watchdog>.py` to check for reverse overwrite before re-diagnosing logic. See `references/cron-sync-two-way-dirty-revert-trap.md`.

### Invariant 17: Hermes Cron Engine no_agent=True Contract & Spend-Guard Model Drift Trap
- **Anti-Pattern:** Creating a script-based watchdog or reconciler as an LLM Agent prompt job (omitting `no_agent=True` or leaving `no_agent: false`). Hermes cron scheduler implements an automated anti-spend guard (#44585 in `cron/scheduler.py`): for unpinned agent jobs (`model: null`), Hermes records the model active at creation (`model_snapshot`). When the global LLM model configuration drifts (e.g. `omni-worker` -> `ag-gemini-pool-3`), Hermes halts the job with a runtime error:
  `⚠️ Cron '<name>' failed: Skipped to prevent unintended spend: global inference config drifted since this job was created (model 'X' -> 'Y'), and this job is unpinned. No inference...`
  This breaks watchdog execution and fires confusing drift alerts to operators.
- **Rule:**
  1. **Mandatory `no_agent=True` for Watchdog Jobs:** All recurring watchdogs, reconcilers, and periodic health checks MUST be configured with `no_agent: true`. This runs the Python script directly, costing 0 LLM tokens and making execution immune to global model configuration drift.
  2. **Relative Script Filename Contract:** Hermes cron strictly enforces `script` paths relative to `~/.hermes/scripts/` (resolving to `%LOCALAPPDATA%\hermes\scripts\`). Absolute paths (e.g. `D:/Taadaa/tools/...`) are rejected at validation time (`Script path must be relative to ~/.hermes/scripts/... Place scripts in ~/.hermes/scripts/ and use just the filename`). Place the script in `%LOCALAPPDATA%\hermes\scripts\` and set `script: "<filename>.py"`. Pair with `workdir` if the script relies on project-relative paths.
  3. **Automated Audit with `reconcile_cronjobs.py`:** Audit violating jobs periodically using `python D:/Taadaa/tools/reconcile_cronjobs.py --dry-run` (or `--apply` to quarantine).

### Invariant 18: Hermes Cron Subprocess Timeout Misclassification Trap
- **Anti-Pattern:** In `Hermes/cron/scheduler.py`, the error classification logic catches any error string containing `"timeout"`, `"timed out"`, or `"readtimeout"` and formats the user-facing alert as:
  `⚠️ Cron '<name>' failed: provider timeout. Fallback chain was exhausted or unavailable. Full details saved in cron output.`
  When a `no_agent: True` script experiences a local Python subprocess timeout (`subprocess.TimeoutExpired: Command ... timed out after 120 seconds`), Hermes catches `"timed out after 120 seconds"` and fires this misleading "provider timeout" alert. Operators and agents waste time assuming the LLM inference provider failed or drifted, when the root cause is purely local script I/O congestion.
- **Rule:**
  1. **Subprocess Timeout Discrimination:** Whenever a `no_agent: True` cronjob alerts with `"provider timeout. Fallback chain was exhausted or unavailable"`, NEVER assume an LLM API error. Immediately inspect `%LOCALAPPDATA%\hermes\cron\output\<job_id>\*.md` to read the raw `subprocess.TimeoutExpired` traceback.
  2. **Binary Prefix Fast-Filter & Persistent Completed Cache on Idempotency Bloat:** When directories contain >9,000 files (e.g. `post-attempts`), never parse JSON across all files. Use `os.scandir` + `open(..., 'rb').read(512)` with compiled regex `re.compile(rb'"status"\s*:\s*"completed"', re.IGNORECASE)` to skip completed receipts.
     - **The HDD Peak-Load Limit:** Even reading 512 bytes on 9,600+ files sequentially hits 15-20ms random head seek latency during peak farm render/sync I/O, causing timeouts (>120s).
     - **Persistent Completed Cache (`.completed_receipts_cache.txt`):** Maintain a persistent cache of immutable completed filenames. Pre-load the set into memory in 0.002s; checking `if entry.name in completed_cache: continue` eliminates file opens completely for historical records, dropping run time from >120s to < 0.05s permanently. Newly completed files are appended to the cache file.
  3. **Claude CLI On-Demand Review Verification:** When asked to review script performance/safety fixes via Claude CLI, invoke `claude -p "<prompt>"` directly with targeted diff/questions and assert pass across edge cases (whitespace variants, multi-byte encodings, fail-safe fallbacks).
  4. **Generous Subprocess Buffer:** Set watchdog runner subprocess timeouts to $\ge 180$s to buffer against periodic NTFS disk load spikes during multi-cloud sync or peak farm operations. See `references/hermes-cron-subprocess-timeout-misclassification.md`.
  5. **Dẹp Bỏ Điểm Số Hình Thức Khi Chốt Phiên:** Khi chốt phiên vận hành/fix watchdog, TUYỆT ĐỐI CẤM nhắc tới điểm số ("Điểm: 100/100" hay "Điểm >= 85"). Báo cáo chỉ ghi nhận: `Verdict: APPROVED (Operational Fast-Pass O(1))` kèm test/lệnh chạy thật. Trường `"score": 100` trong `closeout_gate.py` chỉ phục vụ tương thích ngược cho `safe_push.py`, cấm đưa vào prose giao tiếp với User.

### Invariant 19: Code-Fix vs Historical State Desync & Reconciliation Obligation
- **Anti-Pattern:** When fixing a logic bug that caused phantom successes or false state transitions (e.g. child runner returning exit code 0 on skipped/failed accounts), the agent only patches the execution script (`chatgpt_gpm_direct_reg.py`) but forgets to audit, clean, or reconcile the historical state files (`batch_gpm_5profiles_supervisor_state.json`). Consequently:
  1. **Reporting Inertia & Distrust:** Scheduled watchdogs/reports (`cron_hotmail_gpm_lifecycle_6h_report.py`) continue reading historical state files and reporting high "success" rates (e.g. 567/630 accounts registered) despite zero actual credentials or active sessions, causing user confusion and distrust.
  2. **Pipeline Starvation & Stage Trapping:** Supervisors treat accounts with historical phantom timestamps (`chatgpt_registered_at`) as completed, skipping registration and advancing hundreds of accounts to mature stages (`WAIT_7D` -> `CHANGE_INFO` -> `DONE`) without ever performing the prerequisite operation.
- **Rule:**
  1. **Mandatory Post-Fix State Audit & Reconcile:** Whenever a phantom-success bug is resolved in a runner script, the agent MUST immediately audit the historical state files across all affected clusters (Kibe, Admin).
  2. **Ground-Truth Credential/Session Cross-Check:** Reporting watchdogs MUST NOT rely solely on naive timestamps (`chatgpt_registered_at`) or downstream stage names. They must cross-check with tangible evidence: non-empty credential fields (`chatgpt_password`) or active connection records in the destination registry (e.g. OmniRoute `provider_connections`).
  3. **State Rollback & Re-Queue Protocol:** Any entity identified with a phantom timestamp and missing ground-truth credentials must be rolled back: clear the phantom timestamp, reset the stage back to the prerequisite step (`CHATGPT_REG`), and allow the supervisor to legitimately execute the task.

### Invariant 20: Pre-Session Baseline Fidelity in Rolling Reconciliation (Anti-Baseline Drift Trap)
- **Anti-Pattern:** In shift/session watchdogs reconciling external platform counters (e.g. TikTok Web Following vs script reported delta), the watchdog only scrapes Web snapshots at the **end of each session** (`09:35`), and computes delta against a baseline snapshot with `timestamp <= query_start_iso` (`session_start + 30m`).
  If a machine was skipped or didn't run in the preceding session (Phiên 1 at 06:00), there is **no snapshot taken at the start of Phiên 2 (08:00)**. The query falls back to the most recent snapshot in SQLite — which may be from **24 hours prior** (e.g. yesterday's 10:00 AM daily tracker snapshot).
  Any natural follows, un-follows, or off-cycle actions occurring during those 24 hours are lumped into Phiên 2's delta, causing false positive / negative discrepancy alerts (`lệch (+1)`, `lệch (-2)`).
- **Rule:**
  1. **Max Baseline Age Guard (Enforced in `feed_session_watchdog.py`):** Baseline snapshots older than 4 hours or from a previous calendar day MUST NOT be used to compute session deltas. Flag the entity as `baseline stale (> 4h) | UNPROVEN` and exclude it from the aggregate `total_diff` calculation.
  2. **Pre-Session & Post-Session Scrape Protocol (Two-Point Delta Contract — ĐÃ TRIỂN KHAI):** To permanently eliminate `UNPROVEN` flags and baseline drift without relying on arbitrary daily snapshots, implement pre-session scraping:
     - Prior to dispatching follow commands to devices, the runner (`scripts/hermes_cron/tiktok_runner.py` qua `_scrape_pre_session_following`) invokes `tiktok_account_tracker.py` on candidate usernames to record fresh baseline snapshots.
     - **Bẫy kỹ thuật runner:** (1) Dùng trực tiếp `openpyxl` đọc workbook thay vì import module ngoài gây silent `ImportError`; (2) Khi `row == 0` (Dynamic pool), đọc mapping từ `shift_pool_cycle_state.json` hoặc `SHIFT_POOLS` thay vì so khớp cứng `account_row_index == row`.
     - Post-session watchdog scraping then measures delta over a tightly bounded 15-30 minute window, ensuring 100% telemetry freshness and eliminating stale baseline fallbacks across all shifts.
  3. **Target Account Follower Audit:** When the script reports $N > 0$ follows but Web following shows 0 increase, cross-check the `follower` count of target accounts (`followed` in `follow_result.json`) in `snapshots`. If target accounts gained followers, the follow was successfully committed on the server, and the source counter is merely experiencing TikTok CDN/profile cache propagation delay.
  4. **TikTok Optimistic UI Invariant (User Correction):** TikTok UI is strictly optimistic (immediately turns to "Following" on tap). It only flips to "Follow" when the server un-follows/rejects. There is NO scenario where UI shows "Follow" while the request succeeded due to UI lag. When runner halts on an un-follow signal (`FOLLOW_FAILED`), stopping is the correct fail-safe behavior to protect accounts — never relax the runner logic. See `references/tiktok-web-follow-reconcile-baseline-drift-and-target-audit.md`.

### Invariant 21: Decoupled Pipelines (Feed — Follow — Upload) & Mandatory Pull-to-Refresh Profile Reconcile
- **Anti-Pattern:**
  1. Forcing sequential dependency where feed technical hiccups (app crash, transient socket drop, 0 swipes) cause the runner to skip follow (`sensitive-skip-fail`) and upload for healthy accounts.
  2. Proposing to remove `pull_to_refresh_profile` when inspecting an account profile, believing that viewing the profile directly is sufficient. On TikTok app, viewing a profile directly uses local cache (still showing 'Following') — without pull-to-refresh to force server sync, server un-follows cannot be detected.
- **Rule:**
  1. **Strict Pipeline Decoupling:** Feed, Follow, and Upload MUST execute independently. Feed failure does not block Follow; Follow failure does not block Upload. Only severe account-level security states (`_SENSITIVE_ACCOUNT_WORDS`: `banned`, `checkpoint`, `logged_out`, `captcha`) abort subsequent phases.
  2. **Mandatory Pull-to-Refresh with 3.5s Delay & 2-Pass Polling:** Pull-to-refresh is mandatory to detect silent follow drops. To prevent false-negative un-follow flags caused by proxy/4G latency or loading spinners obscuring the button, use `sleep_after=3.5s` and a 2-pass polling loop with 1.5s intervals before classifying relationship state.
  3. **JIT In-flight Reconnect for Stale Sockets:** Before invoking `reset_atx_agent`, execute `adb.reconnect(timeout=5.0)` to clear the frozen USB transport socket at the device level, preventing cascading timeouts across large fleets. See `references/decoupled-pipeline-and-path-b-verify-invariants.md`.

### Invariant 22: Hotmail/GPM Lifecycle Troubleshooting & Quarantine Disentanglement
- **Anti-Pattern:**
  1. Conflating temporary IP cooldown with broken accounts: In mobile 4G proxy clusters (e.g. MobiProxy 46 ports on Kibe, 5 ports on Admin), a single login failure trips a 24h-48h port-level safety cooldown (`status == 'BLOCKED'`) to protect proxy subnets. Treating these as fatal errors and force-retrying or editing state immediately burns through IP limits and risks subnet-wide checkpointing.
  2. Ignoring Quarantine Deadlock: Accounts reaching 3 consecutive login failures (`login_retry_count >= 3`) transition to `QUARANTINE`. When quarantine grows (e.g. 33 accounts in Admin), the automated supervisor halts all progress on those accounts forever until manual/script intervention clears the dead-end state.
  3. Misinterpreting `DONE_WITHOUT_CHATGPT_REG` telemetry: Treating accounts marked `DONE` without ChatGPT registration as data corruption. On Taadaa Farm, Hotmail accounts are acquired for dual purposes: some are dedicated recovery emails for TikTok/2FA and intentionally bypass ChatGPT Web pool allocation, triggering informational cross-audit warnings rather than pipeline failure.
- **Rule:**
  1. **Discriminate Port-Level Cooldown vs Broken Accounts:** Always verify `ip_action_history` timestamps before touching `BLOCKED` accounts. If `now - last_action < cooldown_window` (e.g. 24h), the state is nominal defense-in-depth, not an active fault.
  2. **Canonical Quarantine Remediation Procedure:** To safely unblock quarantine accounts without corrupting supervisor states:
     - Execute the dedicated reset tool: `python D:/Taadaa/tools/reset_admin_quarantine.py`.
     - Verify atomic state writes: reads state from `D:\Taadaa\runtime\admin\cron-state\batch_gpm_5profiles_supervisor_state.json`, resets `login_retry_count = 0`, sets `status = 'PENDING'`, clears `error = None`, and writes via `.tmp` file before atomic replace.
  3. **Telemetry Informational Filtering:** Distinguish between actionable failures (quarantine deadlock, authentication crashes) and telemetry balance notices (`DONE_WITHOUT_CHATGPT_REG`). Never modify code or invalidate valid `DONE` accounts solely to suppress balance audit tags.
  4. **Subprocess `sys.path` Strip & Millisecond False-Failure Loop:** Khi script đăng nhập/xử lý con tự ý lọc `sys.path` (ví dụ `sys.path = [p for p in sys.path if not ("hermes" in p.lower() and "site-packages" in p.lower())]`), toàn bộ venv packages (`requests`, `playwright`) bị gỡ bỏ, gây `ModuleNotFoundError` ngay tức thì (0.001s). Nhận diện: nếu toàn bộ batch n accounts đều fail với timestamp `at` giống hệt nhau từng mili-giây, đó là lỗi crash môi trường/ImportError, tuyệt đối không đoán mò sang lỗi sai mật khẩu hay mạng. Phải sửa triệt để bẫy strip `sys.path` và chạy `reset_admin_quarantine.py` để giải phóng hàng đợi.

### Invariant 23: Anti-Overengineered Watchdog Metas & Synthetic Rule Elimination
- **Anti-Pattern:**
  1. **Synthetic Blocked Rules:** Watchdog tự sinh rule ảo (e.g. `[Closeout] Unremediated-Rejection`) khi thấy log cũ trong rolling window mà không có cặp approval sau đó, rồi đẩy vào danh sách vi phạm.
  2. **Unsolicited Guidance & Actionable Noise:** Watchdog tự thòng thêm các câu mệnh lệnh thừa như `(Cần Bổ Sung Guidance)` và `💡 Actionable: Operator/Agent cập nhật guidance chi tiết...` gây khó chịu cho operator và phình token.
  3. **Auto-Rewire / Translation Buzzwords:** Tự đếm regex các từ khóa rewrite rồi gắn thêm nhãn lòe loẹt như `🔄 Auto-rewire cứu nguy: N lần` khiến operator thắc mắc về "cái gì auto chuyển hướng ấy".
  4. **Scorecard Drift / Stale Reviewer Invariant:** Hệ thống đã bãi bỏ chấm điểm Scorecard 85 và chuyển sang Closeout cơ học O(1) (Pytest 100% pass + GuardEngine ALLOW), nhưng watchdog vẫn giữ nguyên tên `Closeout Reviewer Gate` và soi theo rubric cũ.
- **Rule:**
  1. **Zero Synthetic Rules:** Chỉ thống kê các rule thực tế bị chặn từ các hook/gate có cấu trúc (`rule_id`, `category`, `reason`), tuyệt đối không tự bịa thêm các synthetic rule ảo như `Unremediated-Rejection`.
  2. **Clean Telemetry Output:** Giữ output đối soát sạch sẽ: `📁 Đối soát: N log files (M dòng)`. Không nhồi nhét buzzword như "Auto-rewire", "Auto-clamped".
  3. **No Unsolicited Actionable Guidance Text:** Tiêu đề thống kê vi phạm chỉ cần `🔥 *Top Quy Tắc Bị Chặn:*`, cấm chêm các câu kêu gọi bổ sung guidance hay đùn đẩy việc cập nhật rule cho operator/agent.
  4. **Closeout O(1) Mechanical Alignment:** Đồng bộ tên và logic của G5 thành `Closeout Gate` (bỏ chữ Reviewer), khớp với các trạng thái cơ học mới (`[GuardEngine ALLOW]`, `CLOSEOUT_PASSED`). Xem [`references/compliance-watchdog-anti-overengineering-and-synthetic-rules.md`](references/compliance-watchdog-anti-overengineering-and-synthetic-rules.md).

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
- [`references/downstream-schema-semantics-and-false-negative-flagging.md`](references/downstream-schema-semantics-and-false-negative-flagging.md) — Case study: Compound credential validation traps (`bool(username and password)`), intentional OTP empty-password semantics, and ground-truth cross-checks.
- [`references/cron-sync-two-way-dirty-revert-trap.md`](references/cron-sync-two-way-dirty-revert-trap.md) — Bẫy 2-way sync cron_sync_watchdog đè ngược file cũ từ runtime dirty revert commit Git.
- [`references/watchdog-timeout-and-file-scan-bottleneck.md`](references/watchdog-timeout-and-file-scan-bottleneck.md) — Case study: Watchdog timeout & file-scan bottleneck in large idempotency directories (>9k files).
- [`references/hermes-cron-no-agent-contract-and-spend-guard-drift.md`](references/hermes-cron-no-agent-contract-and-spend-guard-drift.md) — Case study: Hermes cron engine no_agent=True contract, spend-guard model drift traps, and relative script path resolution.
- [`references/hermes-cron-subprocess-timeout-misclassification.md`](references/hermes-cron-subprocess-timeout-misclassification.md) — Case study: Hermes cron subprocess timeout misclassification ("provider timeout"), raw output inspection, and binary prefix fast-filtering.
- [`references/historical-state-reconciliation-and-cron-report-audit.md`](references/historical-state-reconciliation-and-cron-report-audit.md) — Case study: The "Fixed Code, Forgotten State" trap, phantom ChatGPT registration reconciliation, and system-wide cron report audit checklist.
- [`references/tiktok-web-follow-reconcile-baseline-drift-and-target-audit.md`](references/tiktok-web-follow-reconcile-baseline-drift-and-target-audit.md) — Case study: TikTok Web follow reconciliation, 24h baseline drift from missing pre-session scrapes, and target account follower cross-checks.
- [`references/decoupled-pipeline-and-path-b-verify-invariants.md`](references/decoupled-pipeline-and-path-b-verify-invariants.md) — Invariants on decoupled pipelines (Feed — Follow — Upload) and accurate follow release discrimination in Mode 2 Path B verify.
- [`references/compliance-watchdog-anti-overengineering-and-synthetic-rules.md`](references/compliance-watchdog-anti-overengineering-and-synthetic-rules.md) — Case study: Anti-overengineering in compliance watchdog, eliminating synthetic rules, guidance spam, and aligning mechanical closeout.
