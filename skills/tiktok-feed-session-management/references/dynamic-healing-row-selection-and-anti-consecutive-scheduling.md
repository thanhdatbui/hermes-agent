# Dynamic Healing Row Selection & Anti-Consecutive Scheduling Invariants

## Background & Problem Statement
In the 96h (4-day) TikTok farm nurture cycle:
- Days 0 & 1: Alternating even/odd rows (Row 1, 3, 5 vs Row 2, 4, 6) on follow + feed.
- Day 2: Row 7 (Morning), Row 8 (Noon), and Healing/Rest slot (Evening: 18:00 & 20:00).
- Day 3: Rest Day (0 follow, pure FYP feed + upload) across 3 shifts (Morning 06/08h, Noon 12/14h, Evening 18/20h).

### The Static Assignment Failure
Historically, `tiktok_runner.py` statically hardcoded `healing_row`:
- Day 2 Evening: Hardcoded Row 3 (or 4).
- Day 3 Morning: Hardcoded Row 3.
- Day 3 Noon: Hardcoded Row 4.
- Day 3 Evening: Hardcoded Row 5 (or 6).

**Consequences:**
1. **Consecutive Shift Clash (Kẹp ca):** Row 3 ran Day 2 Evening (20:00), then immediately ran Day 3 Morning (06:00) — only 10 hours apart. Then Day 4 Noon ran Row 3 again (3 times in 48 hours).
2. **Blind to Real Account Health:** Rows suffering heavy follow drop/penalties (e.g., Row 2 with ~58% active cooldown after Day 1) were completely excluded from healing slots because rows 1, 2, 7, 8 were not in the static healing list.

---

## Dynamic Healing Selector (`healing_selector.py`)

### 1. Invariant Rules (Priority Order)

1. **Session 2 Pairing Rule:**
   - Session 2 (08:00, 14:00, 20:00) MUST follow Session 1 (06:00, 12:00, 18:00) of the same ca.
   - Checked via `runner_simple_state.json`: if `last_window` matches the current ca's Session 1, reuse `last_row`.

2. **Hard Anti-Consecutive Rule (Ca Boundary):**
   - Session 1 of any ca MUST exclude `last_row` of the preceding shift.
   - Eliminates consecutive runs on the same devices within 10 hours.

3. **Rest-Day Multi-Shift Separation (cycle_day == 3):**
   - On full rest days, Session 1 of each ca excludes all rows that have already run earlier that day (inspected via `live/YYYY-MM-DD/row-*`).
   - Ensures Ca 1, Ca 2, and Ca 3 rescue 3 distinct rows.

4. **Health Priority Scoring:**
   Among remaining candidate rows:
   $$\text{Score}(R) = 100 \times P_{\text{fail}} + 20 \times P_{\text{young}}$$
   - $P_{\text{fail}}$: Active cooldown or `follow_failed` rate in `D:/Taadaa/tiktok-follow/runs/state/follow_state_*.json`. (P0: Accounts needing trust recovery).
   - $P_{\text{young}}$: Ratio of accounts with < 10 videos from `D:/Taadaa/data/tiktok_tracker.db` (`farm_account_info` joined with `snapshots`).

### 2. Performance & Production Hardening

- **60s In-Memory Cache:** Scanning 400+ follow state JSONs takes ~1.5s. Wrap `_get_recent_follow_fail_rates` and `_get_young_account_rates` in a 60-second in-memory cache to guarantee <10ms evaluation in cron loops and unit tests.
- **Fail-Safe Fallback:** If `healing_selector.py` is missing or fails, catch the exception, emit a structured JSON telemetry warning (`healing_row_fallback`), and fallback to the legacy cycle row (`Row 3, 4, 5, 6`) to prevent cron crash.
- **Structured Telemetry:**
  - Success: `{"event": "healing_row_selected", "row": R, "window": "HH:MM", "cycle_day": D, "cycle_idx": I, "tools_dir": "..."}`
  - Fallback: `{"event": "healing_row_fallback", "row": R, "window": "HH:MM", "error": "...", "error_type": "..."}`
