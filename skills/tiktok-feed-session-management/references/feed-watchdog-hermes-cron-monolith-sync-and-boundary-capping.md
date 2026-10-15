# Feed Watchdog Hermes Cron Monolith Sync & Boundary Capping Invariants

## Context & Root Cause (Incident 15/10/2026)

### 1. The Modular vs Monolith Pitfall in Hermes Cron
- **Root Cause**: `scripts/feed_session_watchdog.py` in repo `tiktok-luot nuoi acc` was refactored into a modular package (`from watchdog.lock import ...`).
- **The Breakdown**: Hermes cron scheduler deploys scripts to `%LOCALAPPDATA%\hermes\scripts\feed_session_watchdog.py`. When Python executes the script from AppData, `sys.path[0]` is `%LOCALAPPDATA%\hermes\scripts\`, where the `watchdog/` folder does NOT exist, throwing `ModuleNotFoundError: No module named 'watchdog'`.
- **Follow Watchdog Collateral**: `follow_session_watchdog.py` imports `feed_session_watchdog as fsw`, which broke both cron jobs simultaneously.
- **Architectural Solution**: 
  - Keep `scripts/hermes_cron/feed_session_watchdog.py` as a standalone, dependency-free monolithic runner with no relative package imports.
  - Keep `scripts/feed_session_watchdog.py` as the repo entrypoint.
  - The shared reconcile helpers block (`RECONCILE_METRICS` through `reconcile_cluster_following`) must be 100% byte-for-byte identical between both files, enforced strictly by `test_reconcile_helpers_in_sync_with_hermes_cron`.

### 2. Time Window Buffer Capping & Microsecond Boundary
- **Boundary Clamping**:
  - Positive buffer (`minutes > 0`): clamped to `end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)`.
  - Negative buffer (`minutes < 0`): clamped to `start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)`.
- **SQLite Timestamp Alignment**:
  - SQLite snapshot timestamps are stored as `%Y-%m-%d %H:%M:%S`.
  - Using `microsecond=999999` for ceiling allowed subsecond datetimes (e.g. `23:58:59.500000 + 1m = 23:59:59.500000`) to escape clamping, formatting to `23:59:59` without incrementing `buffer_capped`. Setting `microsecond=0` guarantees any time past `23:59:59.000000` is strictly capped.
- **Telemetry Observability**:
  - Suppress `[RECONCILE_BUFFER_TELEMETRY]` logs when `minutes == 0` to prevent log bloat.
  - Track `subsecond_capped` metric when capping occurs on an input containing microseconds.

### 3. Reviewer Gate Diff Squashing Rule
- In multi-turn remediation, running `closeout_gate.py` with `--base HEAD~1` extracts only the latest commit's diff (often just test adjustments), causing the AI Reviewer to reject due to "no production changes".
- Always squash intra-session remediation commits onto `origin/master` (`git reset --soft origin/master && git commit`) before review evaluation so the reviewer assesses the complete solution.
