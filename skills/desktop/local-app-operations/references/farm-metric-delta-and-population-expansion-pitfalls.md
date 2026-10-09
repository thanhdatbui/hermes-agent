# Farm Metric Delta Disconnect vs Population Expansion & Formatting Invariants

## Context & Phenomenon
On social media farm dashboards (such as TikTok Farm Dashboard at `kibe:1905`), operators tracking fleet metrics observed two distinct confusion patterns:

### Pattern 1: "Ủa sao mới thấy tăng giờ thấy ghi giảm ở các chỉ số rồi?"
- **Total Accounts:** 1,042 (expanded by +50 accounts from 992 yesterday).
- **Total Followers:** 12,261 (increased by +41 from 12,220 yesterday).
- **Total Likes/Hearts:** 30,554 (increased by +1,034 from 29,520 yesterday).
- **KPI Delta Badges:** Showed red negative values: **`-17`** Followers and **`-85`** Following.
- **Sub-detail Label:** Displayed `📈 Tổng tăng: +-85`.
- **User Perception:** Table leaderboards showed positive accounts (`+5`, `+4`, `+2`), but header KPI showed negative deltas, and the string `+-85` looked broken.

### Pattern 2: "Clgt sao tổng nick còn 54???" (The Midnight Partial Scan Trap)
- **Time:** 00:34 AM (just after midnight).
- **Total Accounts Displayed:** Dropped abruptly from **1,042** to **54**.
- **User Panic:** Operators assumed ~988 accounts were deleted, banned, or lost from the database.

### Pattern 3: "Sao quét ms nhất thiếu nick r đi báo đỏ lòm v" (The Partial-Scan Bulk Aggregation Trap / Phantom Fleet Drop)
- **Time:** 04:11 AM (mid-morning / staggered scan).
- **Accounts:** 1,129 (down 123 accounts from 1,252 yesterday).
- **KPI Metrics in Modal (Biểu Đồ Tăng Trưởng Toàn Farm):**
  * FOLLOWER: 12,409 with massive red drop **`-1,082`**.
  * TIM: 60,139 with massive red drop **`-2,810`**.
  * ĐÃ FOLLOW: 12,916 with massive red drop **`-1,504`**.
- **User Reaction:** Operators see red negative numbers everywhere and assume accounts died or got penalized, when in reality 123 accounts were simply mid-scan.

---

## Root Cause Analysis

### 1. New Account Delta Asymmetry
In snapshot-based tracking schemas (SQLite `snapshots` partitioned by `username ORDER BY timestamp DESC`):
```python
delta_f = (f_val - prev_f) if prev_f is not None else 0
```
- When new accounts enter the fleet on day $D_0$, they have no record on day $D_{-1}$ (`prev_f is None`).
- Their delta is defaulted to `0` to avoid artificial spikes from accounts created long ago outside the farm.
- Consequently, their baseline followers/following/hearts are added to **Cumulative Totals** (`total_followers += f_val`), but contribute **`0`** to **Cohort Growth** (`total_delta_follower += 0`).

### 2. Old Account Churn vs Net Cohort Delta
`total_delta` is computed as the pure algebraic sum of individual account deltas:
$$\text{Total Delta} = \sum_{i \in \text{Fleet}} \delta_i$$
Since new accounts contribute $\delta = 0$, `total_delta` measures **only the net gain/loss of pre-existing accounts**:
- Pre-existing accounts naturally experience unfollows, TikTok bot sweeps, account removals, or transient proxy scrape failures returning 0.
- If pre-existing accounts lost $-58$ followers while gaining $+41$ natural followers, their net delta is $-17$.
- Even though the 50 new accounts added $+58$ followers to the absolute farm pool (raising total from 12,220 to 12,261), the delta indicator accurately reflects that the mature cohort suffered a net drop of $-17$.

### 3. View Granularity Dissonance
- **Top KPI Cards:** Show the aggregate macro sum of the entire fleet ($\sum \delta = -17$).
- **Leaderboard Views (`bxh_follower`, `bxh_following`):** Filter for active growth (`item.delta_follower > 0`) and sort descending. Operators see top accounts gaining $+5, +4, +2$ and conclude the farm is booming, without realizing dozens of dormant accounts each lost $-1$ or $-2$ at the bottom of the list.

### 4. Double-Sign String Interpolation Bug (`+-` Glitch)
In template strings and client-side DOM refresh loops:
```html
<!-- Server HTML Template -->
📈 Tổng tăng: <strong style="color:#22c55e;">+{summary.get('total_delta_following', 0)}</strong>

<!-- Client-side auto-refresh JS -->
bdEl.innerHTML = `... | 📈 Tổng tăng: <strong style="color:#22c55e;">+${formatNum(totDeltaFl)}</strong>`;
```
When `total_delta_following` is negative (e.g. `-85`), string concatenation hardcoding a leading `+` produces `+-85`:
`📈 Tổng tăng: +-85`
This contradictory syntax directly triggers user skepticism and perceived software malfunction.

### 5. Midnight Rollover & Partial Scan Trap (Why Accounts Collapsed to 54)
In batch tracking systems, partial reconciliation runs occur outside the main daily 07:00 scan:
- At **00:10 AM**, an auxiliary script (e.g. `feed_session_watchdog.py`) reconciled only the 54 machines completing the evening feed session.
- It recorded 54 snapshots timestamped `2026-09-25 00:10:37`.
- The dashboard SQL contained:
  ```python
  cur.execute("SELECT substr(MAX(timestamp), 1, 10) FROM snapshots")
  max_dt = cur.fetchone()[0]  # Evaluates to '2026-09-25'
  ```
  And then filtered:
  ```sql
  WHERE substr(timestamp, 1, 10) = ?  -- ? = '2026-09-25'
  ```
- Because only 54 accounts had been scanned so far on `2026-09-25`, the query dropped the remaining 988 accounts (whose latest snapshot was `2026-09-24`).
- **Lesson:** Filtering by `substr(timestamp, 1, 10) = max_dt` creates a recurring time-bomb between 00:00 and the scheduled general scan (07:00). Any partial run instantly hides the rest of the fleet.

### 6. The Partial-Scan Bulk Subtraction Fallacy ("Tổng Trừ Tổng" vs Mismatched Populations)
- Daily aggregation in `get_farm_history()` groups snapshots by `dt = substr(timestamp, 1, 10)`, sums follower/heart/following for all accounts that have a snapshot on that day, and then calculates delta as:
  $$\Delta_{\text{Day}} = \text{SUM}(\text{Followers}_{\text{today}}) - \text{SUM}(\text{Followers}_{\text{yesterday}})$$
- On multi-cluster farms (e.g. 160 machines: Kibe M1-80 + Admin M201-280), large sweeps (1,252 accounts) take 30–60 minutes and run in batches.
- When an operator opens the dashboard while 123 accounts are still pending scan (1,129 scanned):
  - Today's sum: only counts 1,129 accounts = 12,409 followers.
  - Yesterday's sum: counted all 1,252 accounts = 13,491 followers.
  - The bulk subtraction $12,409 - 13,491 = -1,082$ treats the un-scanned accounts as having 0 followers!
  - It creates a massive **phantom drop** (-1,082 followers, -2,810 hearts) and paints the dashboard blood-red, even though actual followers on scanned accounts are healthy or growing.

### 7. The Flawed `< 50%` Heuristic Threshold Trap
- The previous mitigation in Section 5 used:
  `if history[-1]["total_users"] < (history[-2]["total_users"] * 0.5):`
- This heuristic assumed partial scans only happen right after midnight with very small batches (<50% of the farm, e.g. 54 accounts).
- When a scan is **90.2% complete** (1,129 out of 1,252 accounts), $1,129 > 626$ (50%), so the fallback **never triggers**.
- Yet missing just 9.8% of accounts (123 accounts) is enough to create a 4-digit negative phantom delta! A 50% threshold is dangerously loose.

---

## Defensive Engineering Rules & Best Practices

### 1. Safe Delta Formatting Guard (Zero Hardcoded Signs)
Never prepend literal `+` before dynamic numbers. Always use sign-aware helpers:

**Python Server:**
```python
tot_delta_following = summary.get("total_delta_following", 0)
if tot_delta_following < 0:
    following_delta_label = "📉 Tổng giảm:"
    following_delta_color = "#ef4444"
    following_delta_val_str = str(tot_delta_following)
else:
    following_delta_label = "📈 Tổng tăng:"
    following_delta_color = "#22c55e"
    following_delta_val_str = f"+{tot_delta_following}"
```

**JavaScript Client:**
```javascript
const flSign = totDeltaFl > 0 ? '+' : '';
const flColor = totDeltaFl < 0 ? '#ef4444' : '#22c55e';
const flLabel = totDeltaFl < 0 ? '📉 Tổng giảm:' : '📈 Tổng tăng:';
bdEl.innerHTML = `🔗 Nội bộ: <strong style="color:#38bdf8;">+${formatNum(intFl)}</strong> | ${flLabel} <strong style="color:${flColor};">${flSign}${formatNum(totDeltaFl)}</strong>`;
```

### 2. Canonical Sliding-Window & Fleet Roster Anchor (No Calendar Day Truncation)
Never truncate or filter dashboard queries by single calendar day (`substr(timestamp, 1, 10) = max_dt`).
When auxiliary watchdogs run partial scans after midnight, calendar-day filters collapse the dashboard down to just the partial batch.

**Production Sliding-Window CTE Pattern (Zero-Dep & Test-Fixture Safe):**
When `farm_account_info` may not exist in all test fixtures, or when newly tracked accounts in `snapshots` have not yet been synced to the mapping table, use a sliding window over the latest scan timestamp (`timestamp >= date(max_dt, '-2 days')`) and compute cross-day delta against each account's latest snapshot on an earlier day:
```sql
WITH RankedAll AS (
    SELECT id, timestamp, username, uid, follower, following, heart, video, status,
           avatar_thumb, has_avatar,
           ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
    FROM snapshots
),
LatestCurr AS (
    SELECT *
    FROM RankedAll
    WHERE rn = 1 AND timestamp >= date(?, '-2 days')
),
RankedPrev AS (
    SELECT s.username, s.follower, s.following, s.heart, s.video,
           ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.timestamp DESC) as rn
    FROM snapshots s
    JOIN LatestCurr c ON s.username = c.username
    WHERE substr(s.timestamp, 1, 10) < substr(c.timestamp, 1, 10)
)
SELECT
    r1.username, r1.uid, r1.follower, r1.following, r1.heart, r1.video, r1.status, r1.timestamp,
    r2.follower AS prev_follower, r2.following AS prev_following, r2.heart AS prev_heart, r2.video AS prev_video,
    r1.avatar_thumb, r1.has_avatar,
    f.may, f.host_id, f.tik
FROM LatestCurr r1
LEFT JOIN RankedPrev r2 ON r1.username = r2.username AND r2.rn = 1
LEFT JOIN farm_account_info f ON r1.username = f.username
ORDER BY r1.follower DESC, r1.heart DESC
```

**Header Telemetry Timestamp Rule:**
When sorting items by `follower DESC`, `items[0]` is the top-follower account (whose timestamp might be from yesterday's scan, not midnight's run). Always compute `last_scan` using max:
```python
last_scan = max((it["timestamp"] for it in items if it.get("timestamp")), default="") if items else ""
```
This guarantees the header badge (`🕒 Quét: DD/MM HH:MM`) accurately reflects the latest scan activity across the entire fleet.

**Benefits:**
1. **Zero Midnight Collapse:** The 54 accounts updated at 00:10 display their `2026-09-25` stats; the other 988 accounts smoothly retain their `2026-09-24` stats. Total count remains 1,042 at all hours.
2. **Zero Stale Account Resurrection:** Old/retired accounts previously deleted from workbooks (inactive > 2 days) are naturally aged out by the 2-day cutoff.
3. **Fixture Compatibility:** Tests without `farm_account_info` or with partial schemas continue passing cleanly.

### 3. Population Drift Transparency
When displaying cumulative vs delta metrics on dashboards where accounts are dynamically added/removed:
- Expose new account count on the Total Accounts card: e.g. `1,042 (+50 mới)`.
- When diagnosing fleet metric changes for operators, clearly distinguish:
  1. **Macro Farm Total:** Absolute pool expansion ($12,220 \to 12,261 = +41$).
  2. **Cohort Delta:** Net organic trajectory of mature accounts excluding newly registered/imported accounts ($\sum \delta_{mature} = -17$).

### 4. The Single-Glitch Cascade Trap (`status != 'ERROR'` Filtering Invariant)
- **The Glitch:** When a single profile fetch encounters a transient network/proxy timeout or rate-limit, scrapers typically record `status = 'ERROR'` with default values `follower = 0, following = 0, heart = 0`.
- **The Cascade:** In a fleet of 1,000+ accounts, if just ONE account (e.g. `@m.ngc4624` with 54 fl and 109 following) suffers this glitch:
  * That single account is recorded as dropping $-54$ followers and $-109$ following.
  * Even if 30 other accounts gain $+38$ followers and 21 accounts gain $+24$ following, the $-54$ and $-109$ drop from that ONE glitch overwhelms the real gains, flipping the entire farm's indicators red ($-17$ and $-85$).
- **The Fix:** In all CTE snapshot queries (`RankedAll`, `RankedPrev`, `DayUser`), strictly filter:
  ```sql
  WHERE status != 'ERROR'
  ```
  This ensures transient network/scraper errors are discarded, and the dashboard seamlessly falls back to the account's last valid `LIVE` snapshot without zeroing out metrics.

### 5. Farm-wide Historical Time-Series Aggregation & Smooth Midnight Dip Avoidance
When building a farm-wide growth chart (`get_farm_history` / `farmHistoryModal`):
1. **Daily Deduped Aggregation:**
   Always group by day AND username taking the latest snapshot of each day to prevent accounts with multiple scans from inflating daily sums:
   ```sql
   WITH DayUser AS (
       SELECT substr(timestamp, 1, 10) as dt, username, follower, following, heart, video, status,
              ROW_NUMBER() OVER (PARTITION BY substr(timestamp, 1, 10), username ORDER BY timestamp DESC) as rn
       FROM snapshots
       WHERE status != 'ERROR'
   )
   SELECT dt, count(username) as total_users, sum(follower) as total_follower,
          sum(following) as total_following, sum(heart) as total_heart
   FROM DayUser WHERE rn = 1 GROUP BY dt ORDER BY dt ASC
   ```
2. **The Midnight Chart Plunge Trap:**
   If an auxiliary run updates only 54 accounts at 00:10 AM, grouping by date creates a final entry for today with `total_users = 54` and `total_follower = 956`. On an SVG line chart, this renders as a catastrophic vertical drop (plunging from 12,315 down to 956).
3. **Smooth Live Farm Fallback:**
   If the latest day in history has a partial population (`total_users < 0.5 * previous_day_users`):
   ```python
   if len(history) >= 2 and history[-1]["total_users"] < (history[-2]["total_users"] * 0.5):
       farm_data = get_farm_data(db_path)
       s = farm_data.get("summary", {})
       history[-1]["total_users"] = s.get("total", history[-1]["total_users"])
       history[-1]["follower"] = s.get("total_followers", history[-1]["follower"])
       history[-1]["following"] = s.get("total_following", history[-1]["following"])
       history[-1]["heart"] = s.get("total_hearts", history[-1]["heart"])
   ```
   This anchors today's chart point to the live sliding-window total across all 1,042 active accounts, preserving a smooth, continuous growth curve 24/7.

### 6. Active Fleet Carry-Over vs Entity-Level Delta Summation (Immunity to Partial Scans)
To permanently eliminate partial-scan phantom drops:
1. **Rule 1: Never subtract bulk totals across unequal populations ($N_{\text{today}} \ne N_{\text{yesterday}}$):**
   - Bulk subtraction $\sum A - \sum B$ is only valid when $A$ and $B$ are the exact same set of entities.
   - For historical date rollups, if an active account has no snapshot on day $D$ yet, carry forward its latest valid snapshot from day $D-1$ (`status != 'ERROR'`). This guarantees $N_{\text{today}} = N_{\text{fleet}}$ (1,252 accounts), preventing phantom dips during staggered runs.
2. **Rule 2: Tighten or Eliminate the Arbitrary 50% Dip Guard:**
   - Instead of `total_users < 0.5 * prev_users`, use:
     `if len(history) >= 2 and history[-1]["total_users"] < (history[-2]["total_users"] * 0.98):`
     (or compare directly against total active fleet count from `get_farm_data()`).
   - If today's distinct scanned users do not cover $\ge 98\%$ of the fleet, anchor today's chart point and delta directly to the live rolling window `farm_data["summary"]` (which already uses the sliding-window carry-over pattern across all 1,252 accounts).
3. **Rule 3: Sum Account-Level Deltas, Do Not Subtract Fleet Sums:**
   $$\Delta_{\text{Farm}} = \sum_{i \in \text{Fleet}} \delta_i \quad \text{where } \delta_i = \text{curr}_i - \text{prev}_i \text{ (and } \delta_i = 0 \text{ if not yet scanned today)}$$
   An incomplete scan will produce a slightly smaller positive delta (e.g. $+15$ instead of $+38$), but **NEVER** an alarming $-1,082$ negative drop.
4. **Rule 4: In-Progress Scan Visual Indicator:**
   When `total_users < prev_users * 0.98`, the modal header should display a subtle progress indicator (e.g. `⏳ Đang quét đợt mới: 1.129/1.252 nick`) so operators know a batch is currently active.
