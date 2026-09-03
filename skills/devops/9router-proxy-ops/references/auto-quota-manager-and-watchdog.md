# 9Router Watchdog & Auto Quota Manager (5h Rolling Quota)

## 1. Context & Root Cause
- **9Router 429 retry flaw:** When an account hits 429 (quota exhausted), 9Router backoff reaches max 5 min (`300.000ms`) and probes the dead account indefinitely (~300 useless requests/day). This causes fallback latency and provider spam signals.
- **Google AI / Antigravity 5h Quota Cycle:** Quota resets **5 hours from the FIRST request of the cycle**, NOT 5 hours from when 429 occurred.
- **Prompt Caching & Routing Rule:** Round-Robin across multiple accounts destroys Prompt Caching (100% cache miss on account switch). Always use **Fill-First (Sequential)** to maintain 85-95% cache hit rate.

## 2. Architecture & Files
- Supervisor Watchdog: `%APPDATA%\9router\9router_watchdog.ps1` (launched silently via `.vbs`).
- Quota Manager: `%APPDATA%\9router\quota_manager.py` (called by watchdog every 10s).
- SQLite Database: `%APPDATA%\9router\db\data.sqlite`.
- Backup location: `D:\Taadaa\AI-Tools\tools\9router-watchdog\`.

## 3. Quota Manager Logic (`quota_manager.py`)
1. **Auto-Disable on 429:**
   - Detects `errorCode == 429` or `"quota"` in `lastError` for active connections (`isActive = 1`).
   - Retrieves `timestamp` of the first request within the last 6 hours from `usageHistory` (`cycle_start_at`).
   - Sets `isActive = 0` and records `{disabled_at, cycle_start_at, name, provider}` into `kv` table (`scope='quota_cooldown'`).
2. **Auto-Enable after 5h Rolling Window:**
   - Compares `now` against `cycle_start_at`.
   - Once elapsed time >= 5.0 hours, clears `errorCode`, `lastError`, `backoffLevel`, and `modelLock_*`, then sets `isActive = 1`.
   - Removes entry from `kv` cooldown tracker.
