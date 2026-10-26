# Exception-Driven Alerting & 24H Heartbeat Architecture

## 1. Problem Statement & The "Silent Death" Paradox
When designing farm watchdogs to follow the "Silent on Nominal, Loud on Anomaly" policy (to prevent Telegram notification spam), a critical failure mode arises:
- If a watchdog crashes, encounters an unhandled exception, has a broken import, or fails to read its database/files, a naive script returns nothing or exits cleanly.
- The operator experiences "peaceful silence", unaware that the watchdog died weeks ago and critical fleet outages are accumulating.

## 2. Core Tri-State Model
Every watchdog execution must evaluate to one of three states:
1. `NOMINAL`: Verified positive proof of health (source is readable, rows > 0, all metrics pass threshold). -> **STDOUT is EMPTY (silent)**.
2. `ANOMALY`: Measurable metric degradation, stalled queues, or frozen accounts. -> **STDOUT contains actionable formatted alert**.
3. `UNKNOWN`: Unhandled exception, missing/empty source without `allow_empty=True`, database lock timeout. -> **FAIL-CLOSED: AUTOMATICALLY TREATED AS P0/P1 ANOMALY**.

## 3. Implementation Pattern: `CronRun` Context Manager
Located at `cron_alert_core.py` (synced to all script runtimes):
```python
import contextlib
import sys

try:
    from cron_alert_core import CronRun
except ImportError:
    CronRun = None

force = "--force" in sys.argv
run_ctx = CronRun("watchdog_name", force_report=force) if CronRun else contextlib.nullcontext()

with run_ctx as run:
    # 1. Enforce positive source verification (Fail-Closed)
    data = run.require_source(load_data, name="fleet_db", allow_empty=False)
    
    # 2. Register checks
    run.check("frozen_accounts", count_frozen, lambda v: v == 0, severity="P1")
    
    # 3. Format report if anomaly or force
    if anomaly_detected or force:
        msg = format_report(...)
        if run:
            run.set_report(msg)
        else:
            print(msg)
```

### Safety Rules:
- `SystemExit(0)` must be treated as `is_clean_exit` and not recorded as an `UNHANDLED_EXCEPTION`.
- `contextlib.nullcontext()` ensures backward compatibility if `cron_alert_core` is missing in isolated sub-environments.
- State is serialized to `D:/Taadaa/runtime/cron_health/<script_name>.json`.

## 4. The 24H Heartbeat Aggregator (Dead-Man's Switch)
Located at `cron_heartbeat.py`, running daily at **09:00 VN (02:00 UTC)** via cronjob `farm-cron-heartbeat-24h`:
- Does NOT execute individual watchdogs; it audits their state files (`runtime/cron_health/*.json`).
- Compares `now - last_end` against `2 * interval_h + 30m`.
- Flags:
  - `STALE`: Watchdog skipped executions or scheduler died.
  - `HUNG`: `last_start > last_end` and duration exceeded max threshold.
  - `ANOMALY`: Open unresolved anomalies from the last run.
  - `OK`: Clean execution within expected window.
- Transmits **exactly 1 message per 24h** to confirm the monitoring system itself is breathing.
