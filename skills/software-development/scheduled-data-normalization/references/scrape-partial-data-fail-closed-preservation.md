# Scrape Partial Data & Fail-Closed Historical Preservation

## 1. Problem Description
Automated scraping pipelines (such as `tiktok_account_tracker.py` running via cron `daily-tiktok-farm-tracker`) extract account metrics periodically from social platform public profiles (HTML rehydration JSON / endpoints).
Due to platform anti-scraping variations (e.g. TikTok returning page layouts without `stats.followerCount`, Safari mobile user-agent quirks, WAF challenges, or transient throttling), a request may successfully extract metadata (User ID, nickname, heart count, video count) while the follower/following count is returned as `0` or `None`.

### The False Drop Trap
If the recording module blindly inserts `0` into the database:
- `follower: 0`, `following: 0` overwrites the active account's actual metric (e.g. 245 followers, 36 following).
- Delta calculation calculates:
  $$\Delta Follower = 0 - 245 = -245 \quad (-100\%)$$
- Downstream anomaly detection logic flags the account with:
  `⚠️ TỤT BẤT THƯỜNG (-245 / 100%)`
- Operators inspecting the dashboard believe accounts suffered severe drops or mass-unfollows, while on the real device/app the followers are 100% intact.

## 2. Invariant: Fail-Closed Historical Preservation
When automated crawler data is incomplete or suspect:
1. **Never Overwrite with 0 if Historical > 0 (Independent Per-Field Guarding)**:
   If an account is parsed with `follower == 0` (or `following == 0`) but has a previous historical snapshot with positive historical values:
   - Treat `0` as an extraction failure / missing data signal.
   - Guard each field **independently** so an isolated following-count scrape failure does not overwrite history while follower is valid.
   - **Forward-fill** the last known good value and emit structured warning telemetry:
     ```python
     curr_following = int(item_copy.get('followingCount') or 0)
     if prev_row:
         prev_follower, prev_following, prev_heart, prev_video = prev_row
         if curr_follower == 0 and prev_follower and prev_follower > 0:
             curr_follower = prev_follower
             follower_delta = 0
             logging.warning("zero-scrape telemetry: follower preserved for %s", username)
         else:
             follower_delta = curr_follower - (prev_follower or 0)
         if curr_following == 0 and prev_following and prev_following > 0:
             curr_following = prev_following
             following_delta = 0
             logging.warning("zero-scrape telemetry: following preserved for %s", username)
         else:
             following_delta = curr_following - (prev_following or 0)
         heart_delta = curr_heart - (prev_heart or 0)
         video_delta = curr_video - (prev_video or 0)
     ```
   - *Observability requirement*: Always emit a warning log with `zero-scrape telemetry: <field> preserved for <username>` so fleet watchdogs and telemetry pipelines can track scrape degradation.
   - *Testing requirement*: Unit test suites must assert independent branches (follower-only zero, following-only zero, and both zero) and verify that `caplog` captures the expected warning telemetry without false positives.
2. **Dashboard Anomaly Detector Guard**:
   In web dashboards (e.g. `get_farm_data` / `tiktok_dashboard.py`):
   - A drop from positive followers to 0 while `heartCount` remains stable or increases (`delta_h >= 0` and `heartCount > 0`) is characteristic of a scraper failure, NOT account shadowban.
   - Guard `is_anomaly_drop` against zero-follower drops when engagement indicators are healthy.
3. **Database Remediation Protocol**:
   When a bad crawler run inserts zero-follower rows:
   ```sql
   UPDATE snapshots
   SET follower = (
       SELECT prev.follower FROM snapshots prev
       WHERE prev.username = snapshots.username
         AND prev.timestamp < :bad_run_start
         AND prev.follower > 0
       ORDER BY prev.timestamp DESC LIMIT 1
   ),
   following = (
       SELECT prev.following FROM snapshots prev
       WHERE prev.username = snapshots.username
         AND prev.timestamp < :bad_run_start
         AND prev.follower > 0
       ORDER BY prev.timestamp DESC LIMIT 1
   )
   WHERE timestamp >= :bad_run_start
     AND follower = 0
     AND EXISTS (
         SELECT 1 FROM snapshots prev
         WHERE prev.username = snapshots.username
           AND prev.timestamp < :bad_run_start
           AND prev.follower > 0
     );
   ```

## 4. Real Incident & Verification Recipe (TikTok Farm Account Tracker)
- **Incident Signature**: Account `@tuantuannguyen56` (245 followers, 36 following on live app) scraped as `follower=0, following=0, heart=4930, video=8`. Dashboard computed $\Delta = -245$ (-100%) and flagged `⚠️ TỤT BẤT THƯỜNG (-245 / 100%)`.
- **Root Cause in Code**: `record_and_diff()` queried only `(follower, heart, video)` and unconditionally did `curr_follower - (prev_follower or 0)`, then inserted `curr_follower` (0).
- **Hard Fix Implemented**:
  1. In `tiktok_account_tracker.py::record_and_diff()`: Query `(follower, following, heart, video)`. If `curr_follower == 0` and `prev_follower > 0`, preserve `curr_follower = prev_follower`, `curr_following = prev_following`, set deltas to 0, and update `item_copy['followerCount']` before database insert.
  2. Regression unit test: `test_record_and_diff_preserves_followers_on_zero_scrape` in `tests/test_tiktok_account_tracker.py`.
  3. Live verify: Verify `http://127.0.0.1:1905/api/data` returns `is_anomaly_drop: false` and `browser_vision` shows exact historical followers restored without false alarm.

