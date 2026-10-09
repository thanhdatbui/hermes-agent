# Case Study: Dashboard Scroll Jumping, Anomaly Thresholds & Closeout Gate Diff Limits (2026-10-08)

## 1. Background & Root Causes
- **Bug 1 (False Positive Anomaly Drop Alert):**
  Threshold `drop_rate >= 1.0%` for accounts with $\ge 10$ followers falsely triggered red badge `⚠️ TỤT BẤT THƯỜNG (-1 | 1.01%)` on accounts with ~98-100 followers whenever they dropped just 1 follower ($1/99 \approx 1.01\%$).
  *Fix:* Enforce strict invariant that drops $\le 2$ followers (`delta_f >= -2`) are always normal (`is_anomaly_drop = False`). Require $\le -5$ followers drop OR ($\le -3$ followers drop AND $\ge 5.0\%$ drop rate).
- **Bug 2 (Scroll Jumping to Top on Auto-Refresh Across All Tabs):**
  User feedback: *"Ủa cái vụ giật về đầu trang t thấy ở tab nào cũng bị hết mà"*.
  *Root Cause:* 30s polling loop (`setInterval`) rebuilt DOM:
  - Table view called `tbody.innerHTML = ''` and `void tbody.offsetWidth`, temporarily collapsing table height to 0 and clamping `window.scrollY` to 0.
  - Fleet health (`fleet`) and Follow health (`follow_health`) views called `container.innerHTML = '...'`, wiping DOM and resetting scroll.
  - Sub-filter functions called `element.scrollIntoView(...)`, forcing unwanted viewport jumps.

## 2. Universal Solution: Multi-Tab Scroll Preservation & Atomic Swaps
1. **Pass `isAutoRefresh = false` to all render functions:**
   `renderTable(list, showRank, isAutoRefresh)`, `renderFleetHealth(isAutoRefresh)`, `renderFollowHealth(isAutoRefresh)`.
2. **Atomic DOM Replacement:**
   Use `DocumentFragment` and `tbody.replaceChildren(frag)` to avoid height collapse.
3. **Capture & Restore Viewport Coordinates:**
   ```javascript
   const prevY = window.scrollY;
   // ... DOM update ...
   if (isAutoRefresh && window.scrollY !== prevY) {
       window.scrollTo({ top: prevY, behavior: 'instant' });
   }
   ```
4. **Conditional Scrolling:**
   Never invoke `scrollIntoView()` when `isAutoRefresh === true`.

## 3. Closeout Gate Lessons & Hard Invariants
1. **`DIFF_TOO_LARGE` Fail-Fast Ceiling (30,000 bytes):**
   `closeout_gate.py` immediately exits with code 3 if the candidate diff exceeds 30,000 bytes.
   When accumulated new feature code (like follow health UI) combined with tests pushes diff > 30KB:
   - Streamline HTML/JS templates and inline repetitive styling.
   - Compress mock boilerplate in unit tests.
   - Keep total candidate diff strictly under 30KB (< 29.8KB).
2. **Reviewer Scorecard Plateau (76 -> 86/100):**
   Sol Auditor scored 76/100 due to:
   - Missing auto-refresh handling on newly added tabs (`follow_health` falling into `filterData` instead of `renderFollowHealth(true)`).
   - Incomplete boundary testing for anomaly drops.
   *Remediation:* Fixed auto-refresh routing, added `test_anomaly_drop_exhaustive_boundary_matrix` covering 13 edge cases, and achieved 86/100 APPROVED.
