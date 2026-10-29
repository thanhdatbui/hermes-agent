# Multi-Cluster Date Discovery & Mandatory `today` Inclusion (Anti-Unilateral Date Blindspot)

## Problem Summary
In multi-cluster batch watchdogs (e.g. `feed_session_watchdog.py`, `follow_session_watchdog.py`), the watchdog determines which dates to inspect by querying:
```python
all_date_dirs = sorted([
    d for d in os.listdir(LIVE_ROOT)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d >= retention_cutoff and os.path.isdir(os.path.join(LIVE_ROOT, d))
]) if os.path.exists(LIVE_ROOT) else []

dates_to_check = [(d, d == today) for d in all_date_dirs]
```
Where `LIVE_ROOT` is hardcoded to the local controller cluster (`D:/Taadaa/runtime/kibe/live`).

When the local cluster fails to launch or encounters a preflight blocker (such as a port 5038 ADB conflict or missing device lock), the local date folder (e.g. `2026-10-29`) is never created.
Consequently:
1. `all_date_dirs` only contains historical dates (`2026-10-22` to `2026-10-28`).
2. `dates_to_check` completely excludes `today` (`2026-10-29`).
3. Even if remote clusters (e.g. `admin` M201-M280) successfully completed full feed sessions and uploaded videos, the watchdog loops exclusively over historical dates and silently exits without generating any report for `today`. Operators receive zero notifications, giving the impression that the entire farm was abandoned.

## Core Invariant: Multi-Cluster Date Union & Mandatory `today` Check
1. **Mandatory Inclusion of `today`:**
   `today_str = datetime.now(HCMC).strftime("%Y-%m-%d")` MUST ALWAYS be present in `dates_to_check`, regardless of whether local directories exist.
2. **Multi-Cluster Date Union:**
   When discovering historical dates, union the directory listings across ALL configured clusters (`kibe`, `admin`, etc.):
   ```python
   discovered_dates = {today_str}
   for cluster in CLUSTERS:
       c_live = cluster.get("live_root")
       if c_live and os.path.exists(c_live):
           for d in os.listdir(c_live):
               if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d >= retention_cutoff:
                   if os.path.isdir(os.path.join(c_live, d)):
                       discovered_dates.add(d)

   all_date_dirs = sorted(discovered_dates)
   dates_to_check = [(d, d == today_str) for d in all_date_dirs]
   ```
3. **Cluster Failure Visibility:**
   When `today` is evaluated and a cluster directory is missing, the watchdog must NOT silently `continue` and suppress output. It must emit an explicit telemetry notice:
   `🏢 【FARM KIBE - MÁY 1-80】: • Trạng thái: Chưa có lượt chạy nào trong phiên (Chưa chạy / Bị skip / Nghẽn preflight)`
   While reporting the successful cluster runs in full.
