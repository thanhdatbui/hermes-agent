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
1. **Never Overwrite with 0 if Historical > 0**:
   If an account is parsed with `follower == 0` (or `following == 0`) but has a previous historical snapshot with `prev_follower > 0`:
   - Treat `0` as an extraction failure / missing data signal.
   - **Forward-fill** the last known good value:
     ```python
     if curr_follower == 0 and prev_follower and prev_follower > 0:
         curr_follower = prev_follower
         if curr_following == 0 and prev_following:
             curr_following = prev_following
         follower_delta = 0
         following_delta = 0
     ```
2. **Dashboard Anomaly Detector Guard**:
   In web dashboards (e.g. `get_farm_data` / `tiktok_dashboard.py`):
   - A drop from positive followers to 0 while `heartCount` remains stable or increases (`delta_h >= 0` and `heartCount > 0`) is characteristic of a scraper failure, NOT account shadowban.
   - Guard `is_anomaly_drop` against zero-follower drops when engagement indicators are healthy.
3. **Database Remediation Protocol**:
   When a bad crawler run inserts zero-follower rows:
   ```sql
   UPDATE snapshots
   SET follower = prev_follower, following = prev_following
   WHERE timestamp >= :bad_run_start
     AND follower = 0
     AND EXISTS (
         SELECT 1 FROM snapshots prev
         WHERE prev.username = snapshots.username
           AND prev.timestamp < :bad_run_start
           AND prev.follower > 0
     );
   ```
