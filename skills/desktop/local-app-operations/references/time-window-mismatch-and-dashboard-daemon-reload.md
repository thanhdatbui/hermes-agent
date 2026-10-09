# Time Window Mismatch & In-Memory Dashboard Daemon Reload Pitfalls

## 1. Time Window Mismatch (Daily Web Scrape vs Intraday Bot Telemetry)

### Problem Description
On phone farm dashboards (e.g. TikTok Farm Dashboard on port 1905), scraping profile statistics across 1.000+ accounts is bounded to a single daily batch (e.g. 04:00 AM or 07:00 AM) to preserve rotating 4G proxy bandwidth and avoid platform rate-limits / account checkpoints.
Meanwhile, automation bots perform actions (feed surfing, cross-following, account nurturing) continuously in multiple daily shifts (morning, afternoon, evening).

### The Dual-Paradox Trap
If the dashboard attempts to display intraday bot telemetry alongside web snapshot deltas in a single line (e.g. `🔗 Nội bộ: +X | 📈 Tổng tăng: +Y`):
1. **Morning Paradox (Apparent Zero Activity)**:
   - At 04:15 AM right after the daily scrape, web delta shows `+126` (the accumulated fruit of yesterday's shifts).
   - Intraday bot action log (`target_date = today`) is `+0` because new shifts haven't started.
   - Operators immediately misinterpret this as: *"126 follows gained but 0 from internal farm? Why did cross-following fail?"*
2. **Evening Paradox (Subset Greater Than Total)**:
   - By 22:00 after 3 shifts, bot telemetry records `+150` internal follows today.
   - Web snapshot delta is still static at `+126` because the full fleet is only rescraped at dawn.
   - The card shows `🔗 Nội bộ: +150 | 📈 Tổng tăng: +126` — creating the mathematically impossible perception that internal follows exceed total follows.

### Canonical Pattern: Two-Tier Segregation
Separate the card into two distinct time-bound rows:
```html
<div class="kpi-subdetail" id="kpi-following-breakdown">
    <div>📊 Đối soát hôm qua: Bot <strong>+{total_internal_yesterday}</strong> ➔ Web {following_delta_label} <strong>{following_delta_val_str}</strong></div>
    <div>⚡ Tiến độ hôm nay: Bot <strong>+{total_internal_follows}</strong> lượt</div>
</div>
```
- **Row 1 (Yesterday's Audit)**: Pairs yesterday's bot actions (`session_action_stats WHERE target_date = row_prev[0]`) with the web delta between `row_prev` and `max_dt`. Shows the true conversion rate without time distortion.
- **Row 2 (Today's Realtime Progress)**: Displays today's bot actions (`session_action_stats WHERE target_date = max_dt`). Starts at `+0` in the morning and naturally accumulates over the day.

---

## 2. Windows In-Memory Daemon Reload (pythonw.exe + VBS)

### The Stale RAM Trap
When editing single-file Python HTTP servers (`tiktok_dashboard.py`, `server.py`) launched via detached background VBS wrappers (`start_tiktok_dashboard_hidden.vbs` running `pythonw.exe`), modifying the script on disk does NOT update the active server.
The in-memory process continues serving the old HTML/JS templates compiled into RAM when it started days or weeks prior. Hard-refreshing browser tabs will continue rendering obsolete UI.

### Recovery Recipe
1. Terminate the active port listener process explicitly:
   ```powershell
   Get-NetTCPConnection -LocalPort 1905 -ErrorAction SilentlyContinue | ForEach-Object {
       Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
   }
   ```
2. Relaunch via the canonical headless VBS launcher:
   ```bash
   wscript D:/Taadaa/tools/start_tiktok_dashboard_hidden.vbs
   ```
3. Verify HTTP 200 via a fast probe before notifying the user:
   ```bash
   python -c "import urllib.request; resp = urllib.request.urlopen('http://127.0.0.1:1905/', timeout=5); print(resp.status)"
   ```
4. Advise operator to Pull-to-Refresh on mobile browsers to flush client-side cached JS templates.

---

## 3. Closeout Gate Audit Binding vs Working Tree Cleanliness

### Binding Mismatch Root Cause
`closeout_gate.py` enforces immutable cryptographic audit binding (`resolve_audit_binding`):
- When running against a committed revision (`--base HEAD~1`):
  Any dirty working-tree edits on files belonging to `HEAD` trigger:
  `binding mismatch: staged/working-tree candidate overlaps committed HEAD`
- The pipeline requires an unambiguous review target:
  - Either review the committed `HEAD` with its working-tree files clean.
  - Or review the uncommitted changes in **Staged Mode** (`git add` allowlisted files with zero unstaged overlap).
- Never leave partially edited files overlapping committed HEAD when requesting closeout evaluation.

### Partial Staging Mismatch in Targeted Mode (`staged != --files`)
When `--files <F1> <F2> ...` is passed:
`closeout_gate.py` checks whether any targets are staged in the git index:
```python
staged = _z_paths(_git_bytes(repo, "diff", "--cached", "--name-only", "-z"))
if staged:
    if staged != targets:
        raise ValueError(f"staged files {staged} != --files targets {targets}; unstage extras or adjust --files")
```
- If an operator or subagent ran `git add <F1>` but left `<F2>` unstaged in the working directory, the gate fails immediately with `staged files [F1] != --files targets [F1, F2]`.
- **Invariant**: EITHER all target files must be staged (`git add -A <targets>` with zero unstaged edits left on them), OR all target files must remain completely unstaged in working tree (`git diff HEAD`). Never half-stage targets.

### `DIFF_TOO_LARGE` Fail-Fast Guard (> 30,000 bytes)
`closeout_gate.py` enforces an O(1) diff ceiling of 30,000 bytes to prevent flooding reviewer context with monolith diffs:
`GATE-FAIL(diff-too-large): targeted diff quá lớn (X > 30000 bytes)`
- Adding new/untracked auxiliary files to `--files` causes git to generate a full-file diff against `/dev/null`. If the new file is 9–10KB, it adds thousands of diff characters, pushing the total targeted diff past 30KB.
- **Remediation**:
  1. Scope `--files` strictly to the primary code and test files under review for the current task.
  2. Verify that unit tests import and validate any auxiliary modules without needing to force large untracked auxiliary files into the reviewer's candidate diff.

---

## 4. Single-Page Dashboard Auto-Refresh Scroll Snapping & Anomaly Thresholds

### Auto-Refresh Scroll Snapping to Top (DOM Height Collapse)
In periodic auto-refreshing dashboards (e.g. 30s `setInterval` fetching `/api/data`):
- Wiping table rows via `tbody.innerHTML = ''` and triggering forced reflow / fade animation (`void tbody.offsetWidth; tbody.classList.add('table-fade')`) causes the table height to collapse to zero for several milliseconds.
- When document height drops below the user's current scroll offset, the browser forcibly clamps `window.scrollY` to 0. When new rows populate, the user gets jarringly kicked to the top of the page while browsing mid-list.
- **Atomic Swap & Scroll Retention Pattern**:
  ```javascript
  function renderTable(list, showRank, isAutoRefresh = false) {
      const tbody = document.getElementById('tableBody');
      if (!isAutoRefresh) {
          tbody.classList.remove('table-fade');
          void tbody.offsetWidth;
          tbody.classList.add('table-fade');
      }
      const frag = document.createDocumentFragment();
      list.forEach(item => {
          const tr = document.createElement('tr');
          // build tr...
          frag.appendChild(tr);
      });
      const prevY = window.scrollY;
      tbody.replaceChildren(frag); // Atomic swap: zero height collapse
      if (isAutoRefresh && window.scrollY !== prevY) {
          window.scrollTo({ top: prevY, behavior: 'instant' });
      }
  }
  ```

### False-Positive Anomaly Drop Alert on Small Accounts (-1/-2 Normal Variance)
- On accounts with ~50-100 followers, losing just 1 follower produces a `drop_rate` of $1 / 99 \approx 1.01\%$.
- A naive threshold like `delta_f < 0 and drop_rate >= 1.0%` triggers alarming red badges (`⚠️ TỤT BẤT THƯỜNG (-1 | 1.01%)`) on accounts experiencing normal daily variance (accidental unfollows, bot purges).
- **Hard Lower Bound Invariant**:
  ```python
  # Always ignore normal drops of 1-2 followers regardless of percentage
  is_anomaly_drop = (delta_f <= -5) or (delta_f <= -3 and drop_rate >= 5.0 and f_val >= 10)
  ```
  Losing 1 or 2 followers (`delta_f >= -2`) is strictly treated as normal variance (`is_anomaly_drop = False`).
