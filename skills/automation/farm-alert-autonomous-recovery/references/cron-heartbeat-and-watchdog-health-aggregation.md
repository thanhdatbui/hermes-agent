# Cron Heartbeat and Watchdog Health Aggregation Architecture

## 1. Daily 24H Heartbeat Overview (`cron_heartbeat.py`)
- **Trigger**: Runs at 00:00 UTC (07:00 VN) daily via cronjob `farm-cron-heartbeat-24h` (Job ID: `d0c72ffc842b`).
- **Target Health Directory**: `D:/Taadaa/runtime/cron_health/<script_name>.json`.
- **Status Evaluation**:
  - `NO_STATE` (`⚪`): No JSON state file exists at `D:/Taadaa/runtime/cron_health/<script_name>.json` (script hasn't run or isn't wrapped with `CronRun`).
  - `ANOMALY` (`⚠️`): State JSON has `"status": "ANOMALY"`, reporting `len(anomalies)` unresolved issues.
  - `STALE` (`❌`): `age_h > max_age` (where `max_age = interval_h * 2 + 0.5`).
  - `OK` (`✅`): State JSON has `"status": "NOMINAL"` within `max_age`.

## 2. Standardizing Watchdogs with `CronRun` (`cron_alert_core.py`)
To ensure watchdogs adhere to "Silent on Nominal, Loud on Anomaly" and report health to the daily heartbeat:
```python
from cron_alert_core import CronRun

with CronRun(script_name="<script_name>") as run:
    # 1. Require critical data source (fails closed if empty/unreadable)
    source_data = run.require_source(load_fn, name="input_source")
    
    # 2. Add domain checks
    run.check("HEALTH_METRIC", value, ok=lambda v: v > 0, severity="P1", msg="Detail message")
    
    # 3. Explicit anomaly recording
    if unexpected_condition:
        run.anomaly(code="ANOMALY_CODE", message="Specific issue description", severity="P1")
```
- On context exit, `CronRun` calculates runtime duration, evaluates overall status (`NOMINAL` vs `ANOMALY`), and writes `D:/Taadaa/runtime/cron_health/<script_name>.json`.
- Standard output is suppressed unless `status == "ANOMALY"`, keeping Telegram cron channels clean.

## 3. Diagnosing `gate_compliance_watchdog` Anomalies
`gate_compliance_watchdog.py` scans logs across `logs/` and `runtime/audit_logs/` over a rolling window (default 6h) auditing 10 mechanical gates.
- When `gate_compliance_watchdog` flags ANOMALY in heartbeat:
  1. Inspect `D:/Taadaa/runtime/cron_health/gate_compliance_watchdog.json`.
  2. Review `anomalies` / `top_blocked_rules`:
     - `[Worker Dispatch] subagent_edit_blocked`: Subagent attempting edits to unauthorized/protected files.
     - `[Worker Dispatch] investigate`: Open-ended goals dispatched without an exact Patch Contract O(1).
     - `[Anti-Scan & Terminal] GUARD_DANGEROUS_ROOT`: Commands scanning broad directories from root (`/d/Taadaa`, `C:/`).
     - `[Anti-Scan & Terminal] GUARD_DEVICE_LOCK_REQUIRED`: Farm device operations attempted without JIT device lock.
     - `[Cronjob Window] CONSOLE_WINDOW`: Jobs firing during prohibited farm maintenance/reboot windows.
  3. Run focused check: `python D:/Taadaa/tools/gate_compliance_watchdog.py --hours 6` for live status.

## 4. Inspection & Tool Location Quirk
- **Protected script paths**: Files under `~/.hermes/scripts/` or touched by guard hooks are blacklisted by Hermes self-protection guards against direct `read_file`.
- **Authoritative source**: Always inspect tool and watchdog code at `D:/Taadaa/tools/<script_name>.py`.
- **Avoid shell scans**: Terminal `find /d/Taadaa ...` is blocked by the Coordinator terminal guard. Use targeted path checks or narrow directory listing.
