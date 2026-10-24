# Adaptive Biological Shift-Pool Architecture & Watchdog Reporting Contract

## 1. Context & Architecture Overview
To completely break deterministic network correlation fingerprints (Anti-Pattern Bot / Anomaly Dispersion) where all 160 devices wake up the exact same slot at the exact same hour, the farm organizes accounts into 3 biological shift pools:

- **Ca 1 (Morning: 06:00 & 08:00):** Pool `{Row 1, Row 2, Row 7}`
- **Ca 2 (Noon: 12:00 & 14:00):** Pool `{Row 3, Row 4, Row 8}`
- **Ca 3 (Evening: 18:00 & 20:00):** Pool `{Row 5, Row 6}` (Day 0 & Day 1); Day 2 & Day 3 Rest / Organic Healing

### Core Operational Invariants:
1. **Day 0 (Day 1 of 4d cycle):** Each machine independently picks the healthiest account (Rank 1: boosted > healthy > youngest) from the shift pool.
2. **Day 1 (Day 2 of 4d cycle):** Each machine picks Rank 2 from remaining accounts in the pool.
3. **Day 2 (Day 3 of 4d cycle):** Each machine picks Rank 3 (remaining account in Ca 1/Ca 2). Ca 3 runs dynamic organic rest.
4. **Day 3 (Day 4 - Rest Day):** 3x Dynamic healing across all slots via 3-tier funnel.
5. **"S2 bám S1" (Session 2 Sticking Invariant):** Session 2 in the same shift on the same machine MUST stick 100% to the exact row chosen by Session 1 (`today_shift_sessions[ca][machine]`).
6. **Zero Starvation:** 100% of all 8 rows across 160 machines are exercised during the 3 active days before entering Rest Day.

---

## 2. Shift Pool Selector (`shift_pool_selector.py`)

- **State File:** Atomic JSON state persisted at `D:/Taadaa/runtime/kibe/cron-state/shift_pool_cycle_state.json`.
- **State Schema:**
  ```json
  {
    "date": "2026-10-24",
    "cycle_idx": 3,
    "cycle_history": {
      "1": {"1": [2], "2": [2], "3": [2]},
      "2": {"1": [4], "2": [4], "3": [4]},
      "3": {"1": [6], "2": [6], "3": [6]}
    },
    "today_shift_sessions": {
      "1": {"1": 2, "2": 2, "3": 2}
    }
  }
  ```
- **Reset Logic:** When `cycle_idx` changes (every 4 days from `date(2026, 10, 11).toordinal()`), `cycle_history` resets to allow fresh ranking for the new cycle.

---

## 3. Watchdog Reporting & Header Taxonomy

1. **Header Representation (`_row_or_pool_label`):**
   - When running explicit static rows (`active_row > 0`): Report prints `(Row {active_row})`.
   - When running shift pool dynamic (`active_row <= 0`): Report MUST NOT print `(Row 0)` or flat `Row`. It extracts the pool label based on shift window:
     * Ca 1: `(Pool {1, 2, 7})`
     * Ca 2: `(Pool {3, 4, 8})`
     * Ca 3: `(Pool {5, 6})`
     * Unspecified / Rest: `(Dynamic)`
   - Applied consistently across Feed, Follow, Upload, and Farm Alert headers.

2. **Per-Machine Slot Traceability (`[Tik X]` Tagging):**
   - In `reconcile_cluster_following`, when in dynamic mode (`slot_idx < 0`), the report inspects actual executed accounts from `all_machines` or workbook slots.
   - Traceability output format:
     `    - M{m} [Tik {tik_idx}] (@{username}) : script X lượt - web Y lượt - khớp`
   - Explicitly displays `[Tik X]` alongside `@username` so operators immediately see which slot ran without consulting raw manifests.
