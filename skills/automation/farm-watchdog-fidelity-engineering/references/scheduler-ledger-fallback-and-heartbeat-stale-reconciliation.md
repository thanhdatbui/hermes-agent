# Scheduler Ledger Fallback & 24H Heartbeat Stale Reconciliation

## 1. Problem Statement: The "Forgotten Telemetry" Stale Report Trap
On physical automation farms, scheduled watchdogs (e.g., `farm_render_download_watchdog`, `cron_hotmail_gpm_lifecycle_6h_report`, `cron_gmail_gpm_2fa_6h_report`) often execute reliably via scheduler daemons (`jobs.json`), producing complete markdown logs in scheduler output directories.

However, if individual watchdog scripts omit the `CronRun` telemetry context manager or fail to write execution snapshots to `runtime/cron_health/<name>.json`:
- The 24H Heartbeat aggregator (`cron_heartbeat.py`) relies exclusively on static `.json` files.
- Stale snapshots from days prior remain on disk (e.g. 75h ago).
- The daily 09:00 VN heartbeat issues a barrage of false positive alerts:
  `❌ farm_render_download_watchdog: STALE: Lần cuối 75.0h trước (vượt trần 12.5h)`
- Operators assume the fleet scheduler crashed when the jobs actually ran nominal 3 hours prior.

---

## 2. Core Architectural Root Causes
1. **Unilateral Telemetry Dependency:** Relying on target scripts to remember to write specialized JSON status files creates a single point of telemetry failure across dozens of scripts.
2. **Schedule Interval Drift:** Jobs changed in `jobs.json` (e.g. changing `gpm-gmail-nurture` from every 6h to every 12h `0 */12 * * *`) while `WATCHDOG_SPECS` in the aggregator remains statically hardcoded to `interval_h: 6`. The threshold `max_age = interval_h * 2 + 0.5` becomes 12.5h, causing natural 12h runs to trip the stale threshold.
3. **Guard String Sensitivity:** In automated guard environments, avoid hardcoding root hook paths or raw system directories inside contract files. Paths must be resolved dynamically via environment variables or `Path.home()`.

---

## 3. Resilient Multi-Tier Telemetry Contract

### Fallback to Scheduler Execution Ledger (`jobs.json`)
The aggregator must treat the scheduler daemon's execution ledger as a canonical fallback source of truth:
```python
def load_scheduler_runs() -> Dict[str, Dict[str, Any]]:
    jobs_file = Path(os.environ.get("JOBS_CACHE_FILE", Path.home() / "AppData" / "Local" / "hermes" / "cron" / "jobs.json"))
    if not jobs_file.exists():
        fallback = Path("D:/Taadaa/Hermes/deploy/hermes-home/cron/jobs.json")
        jobs_file = fallback if fallback.exists() else None
    if not jobs_file:
        return {}
    try:
        data = json.loads(jobs_file.read_text(encoding="utf-8"))
        job_list = data.get("jobs", data) if isinstance(data, dict) else data
        return {j["script"][:-3]: j for j in job_list if j.get("script", "").endswith(".py")}
    except Exception:
        return {}
```

### Direct Timestamp Comparison & Clock Drift Protection
In `evaluate_heartbeat(now)`:
1. Extract `sched_run = sched_runs.get(name)`.
2. Parse `dt_sched = fromisoformat(sched_run["last_run_at"])`.
3. **Future Timestamp Filter:** Ensure `if dt_sched > now: dt_sched = None` to prevent clock skew or mock artifacts from distorting unit tests.
4. If `state_file` does not exist OR `dt_sched > last_end`:
   - Promote `last_end = dt_sched`.
   - Update `status = "NOMINAL" if sched_run.get("last_status") == "ok" else "ANOMALY"`.
   - Compute `age_h = round((now - last_end).total_seconds() / 3600.0, 1)`.

---

## 4. Multi-Tier Parity Synchronization Rule
Whenever modifying watchdog scripts or heartbeat aggregators across local tools, deploy repo, and runtime directory:
Execute `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py --force` to ensure zero reverse-overwrite dirty-revert traps.
