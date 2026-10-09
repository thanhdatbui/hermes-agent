# Partial-Scan Cumulative History Remediation & Windows CRLF EOL Recovery

## Core Lessons from TikTok Farm Dashboard Closeout (2026-10-06)

In data dashboard and time-series history tracking on phone farms, periodic scanning often yields partial coverage (e.g. 363/1254 machines scanned so far today, or network drop leaving 235 machines unscanned yesterday). This creates specific audit and review failure modes under Sol Auditor (:20129).

### 1. Cumulative State Forward-Fill vs Phantom Delta Traps
- **The Phantom Delta Trap:** When a dashboard aggregates snapshots per day (`GROUP BY dt`) and applies a live summary override when today's scan is partial, yesterday's unscanned accounts (e.g., 235 accounts with 26 following) vanish from yesterday's total and reappear today in the full summary, generating a fake delta (e.g., `+26 following`) that alarms farm operators.
- **Incremental State Forward-Fill:** Instead of daily group-by, process snapshots chronologically. Carry forward the latest valid snapshot for each account across days.
- **First-Observation Zeroing (Invariant):** A newly discovered account in the database must contribute **0** to that day's delta (`delta_follower`, `delta_following`, `delta_heart`, `delta_video`). Adding the full lifetime value of a newly observed account to that day's delta inflates growth metrics and triggers reviewer rejection.
- **Calendar-Day KPI Alignment:** When reporting "yesterday's delta", never rely on array indexing (e.g. `history[-2]`), because skipped scan days or partial lags cause `h[-2]` to point to 2 or 3 days ago. Compute the previous calendar date explicitly:
  ```python
  previous_date = datetime.strptime(current_date, "%Y-%m-%d").date() - timedelta(days=1)
  ```
  If no snapshot exists for that exact calendar date, return safe `0` rather than attributing older deltas to yesterday.

### 2. Roster Denominator & Coverage Observability
- **Authoritative Roster Handling:** If an account roster table (`farm_account_info`) exists, its account set is authoritative even when empty.
  - An empty roster means 0 active users, 0 scanned users, and 0.0 coverage.
  - The coverage denominator must be `len(roster)` (including accounts in the roster that have never yet received a snapshot), not just `len(scanned_users)` or `len(observed_users)`.
- **Explicit Scan Telemetry Fields:** Every historical record must expose:
  - `total_users`: Total active accounts in roster.
  - `scanned_users`: Accounts actually observed on that date.
  - `coverage`: Ratio `scanned_users / total_users`.
  - `forward_filled_users`: Accounts carried forward from earlier snapshots.
  - `partial_scan`: Boolean flag indicating incomplete scan.

### 3. Fail-Closed Error Logging vs Silent Exception Swallowing
- Never swallow exceptions with bare `except Exception: pass` in telemetry and KPI extraction. Sol Auditor penalizes bare passes in data layers.
- Always log with module logger and capture traceback:
  ```python
  except Exception:
      logger.warning("Failed to read action statistics; using zero safe values", exc_info=True)
  ```

### 4. Windows CRLF vs LF EOL Churn During Worker Editing
- **The Issue:** When worker agents or editing scripts save files with LF on Windows while the repository baseline is CRLF, `git diff --numstat` explodes (e.g., +2712 / -2662 on a 2600-line file) even though only ~100 lines changed.
- **The Danger:** Unchecked EOL churn blows past the 24,000-byte Sol Web diff budget, forcing fallback to Terra Codex or incurring heavy truncation penalties from the reviewer.
- **The Fix:** Run `unix2dos <target_files>` before staging and review. Verify with:
  ```bash
  git diff --ignore-space-at-eol --numstat -- <file>
  ```
  Ensure real semantic additions and deletions match the expected line budget before launching `closeout_gate.py`.
