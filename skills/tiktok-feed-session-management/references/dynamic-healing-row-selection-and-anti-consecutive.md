# Dynamic Healing Row Selection & Anti-Consecutive Scheduling

## Context & Problem
In the 96-hour 4-day farm cycle, Day 2 Shift 3 (18h/20h) and Day 3 (Rest Day: Shifts 1, 2, 3) are designated healing slots (`TAADAA_REST_DAY_NO_FOLLOW = 1`, pure FYP feed, 0 follows, background upload checks).

Previously, healing rows were hardcoded statically:
- Day 2 Shift 3: alternating Row 3 / Row 4.
- Day 3: Shift 1 = Row 3, Shift 2 = Row 4, Shift 3 = Row 5 / Row 6.

### Critical Operational Flaws of Static Rotation:
1. **Consecutive Shift Trap ("Kẹp ca"):**
   Row 3 running on Day 2 Shift 3 (finished 20:00) was scheduled again on Day 3 Shift 1 (starting 06:00). Running the same physical devices and accounts twice within 10 hours created biological congestion and ran 3 times within 48h.
2. **Blind to Real Farm Health:**
   Rows suffering massive follow drops / active cooldowns (e.g. Row 2 having >57% active cooldowns) were completely excluded from healing slots because static logic only allowed Rows 3, 4, 5, 6.

---

## Architecture: Data-Driven Healing (`healing_selector.py`)

Located at `D:/Taadaa/tools/healing_selector.py` and invoked by `scripts/hermes_cron/tiktok_runner.py`.

### 1. Invariants & Constraints:
- **Session 2 Pairing Rule:** Session 2 (08h, 14h, 20h) MUST match Session 1 (06h, 12h, 18h) of the current shift (via `runner_simple_state.json` `last_window`).
- **Anti-Consecutive Boundary Rule:** Shift 1 of any shift MUST exclude `last_row` from the preceding shift to prevent 10h back-to-back runs.
- **Rest Day Distribution Rule:** On Day 3 (Rest Day), candidate rows exclude any row already healed today (checked via `runtime/kibe/live/YYYY-MM-DD/row-*-*`), ensuring 3 distinct rows are healed across the 3 shifts.

### 2. Scoring Formula:
$$\text{Score}(R) = 100 \times P_{\text{fail}}(R) + 20 \times P_{\text{young}}(R)$$

- **$P_{\text{fail}}(R)$ (P0 Urgent):** Percentage of accounts in Row $R$ with active cooldown (`now < cooldown_until_at` / `today <= cooldown_until_date`) or recent follow failure from `D:/Taadaa/tiktok-follow/runs/state/follow_state_*.json`.
- **$P_{\text{young}}(R)$ (P1 Foundation):** Percentage of accounts in Row $R$ with $< 10$ videos in SQLite `farm_account_info` & `snapshots`.

### 3. Performance & Clean Loading Patterns:
- **60-Second In-Memory Cache:** `_get_recent_follow_fail_rates` and `_get_young_account_rates` cache results for 60s to prevent disk churn across rapid cron checks or test runs.
- **No `sys.path` Mutation in Runtime Flows:** Use `importlib.util.spec_from_file_location` to load `healing_selector.py` dynamically without mutating `sys.path` in `_determine_row`.
- **Structured Telemetry:**
  - Success: `{"event": "healing_row_selected", "row": R, "window": "HH:MM", "cycle_day": D, "cycle_idx": I, "tools_dir": "..."}` to stdout.
  - Exception fallback: `{"event": "healing_row_fallback", "row": R_fb, "window": "HH:MM", "error_type": "...", "error": "..."}` to stderr.
- **Backwards-Compatible Fallback:** If `healing_selector` is missing or crashes, gracefully fallback to original static row mapping (Row 3/4/5/6) so cron execution never stalls.
