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

---

## 3. Verification Protocol for Watchdogs & Reports
1. **Syntax & Compilation:** Run `python -m py_compile <script.py>`.
2. **Deterministic Telemetry Test:** Run focused pytest verifying AST structure, telemetry output to stderr, and empty-input edge cases.
3. **Dry-Run / Live Probe:** Execute with `--dry-run` or direct execution ensuring stdout contains only formatted report text while metrics route to stderr.
4. **OneDrive & Deployment Parity:** Always sync updates between repo deployment path (`deploy/hermes-home/scripts/`) and shared operational directory (`OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`).

---

## 4. References & Case Studies
- [`references/zero-reporting-blindspots-and-watchdog-fidelity.md`](references/zero-reporting-blindspots-and-watchdog-fidelity.md) — Case study: Eliminating blindspots in Taadaa Farm cron reports (ADB offline isolation, state desync fallback, NEEDS_LOGIN separation, starving slot alerts).
- [`references/watchdog-timeout-and-file-scan-bottleneck.md`](references/watchdog-timeout-and-file-scan-bottleneck.md) — Case study: Watchdog timeout & file-scan bottleneck in large idempotency directories (>9k files).
