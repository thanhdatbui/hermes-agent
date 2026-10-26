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
- **Rule:**
  1. **Explicit Cluster Runtime Contracts:** Pass cluster-specific Python executables, repo roots, and workbooks configured per cluster (e.g. `admin.yaml` vs `kibe.yaml`).
  2. **Strict Dual Telemetry Requirement:** Watchdogs dispatching to remote hosts via SSH must parse structured JSON emitted on stdout or fetch remote summary artifacts before reporting.
  3. **Zero-Count Remote Alert:** If a cluster configured for batch execution returns 0 machines selected, 0 success, and 0 failed, the watchdog must flag this anomaly (`⚠️ Cluster Admin: Không thu thập được telemetry / 0 máy được chọn`) rather than silently suppressing the missing cluster. See `references/cross-cluster-multi-host-watchdog-parity.md`.

---

## 3. Verification Protocol for Watchdogs & Reports
1. **Syntax & Compilation:** Run `python -m py_compile <script.py>`.
2. **Deterministic Telemetry Test:** Run focused pytest verifying AST structure, telemetry output to stderr, and empty-input edge cases.
3. **Dry-Run / Live Probe:** Execute with `--dry-run` or direct execution ensuring stdout contains only formatted report text while metrics route to stderr.
4. **OneDrive & Deployment Parity:** Always sync updates between repo deployment path (`deploy/hermes-home/scripts/`) and shared operational directory (`OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`).

---

## 4. References & Case Studies
- [`references/cross-cluster-multi-host-watchdog-parity.md`](references/cross-cluster-multi-host-watchdog-parity.md) — Root causes and contracts for cross-host watchdog execution and telemetry collection (Kibe local vs Admin remote).
- [`references/exception-driven-alerting-and-24h-heartbeat.md`](references/exception-driven-alerting-and-24h-heartbeat.md) — Exception-driven alerting, fail-closed tri-state model, and the 24h heartbeat aggregator (Dead-Man's Switch).
- [`references/gateway-agent-max-turns-budget-and-refund-bug.md`](../../hermes/hermes-gateway-ops/references/gateway-agent-max-turns-budget-and-refund-bug.md) — Xử lý trần 20 tool iterations bóp nghẹt watchdog/coordinator và bug refund() conversation_loop.
- [`references/zero-reporting-blindspots-and-watchdog-fidelity.md`](references/zero-reporting-blindspots-and-watchdog-fidelity.md) — Case study: Eliminating blindspots in Taadaa Farm cron reports (ADB offline isolation, state desync fallback, NEEDS_LOGIN separation, starving slot alerts).
- [`references/watchdog-timeout-and-file-scan-bottleneck.md`](references/watchdog-timeout-and-file-scan-bottleneck.md) — Case study: Watchdog timeout & file-scan bottleneck in large idempotency directories (>9k files).
