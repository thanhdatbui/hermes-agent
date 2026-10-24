# Adaptive Biological Schedule: Shift Pool Dynamic Account Selection Contract

## 1. Context & Motivation
Running static rows farm-wide (e.g. all 160 machines concurrently waking up Row 1 at 06:00 on Day 0) creates strong **network correlation / temporal bot fingerprints** detectable by TikTok Anti-Abuse algorithms. Furthermore, static schedules cannot adaptively prioritize viral accounts or heal penalty flags without disrupting farm alignment.

**The Solution:** Transition from mechanical synchronization to an **Adaptive Biological Schedule (Shift Pools)**:
- Group 8 rows into 3 diurnal shift pools matching biological usage habits (morning, noon, evening).
- On each machine, select accounts adaptively within that shift's pool according to health rankings.
- Preserve habit consistency: morning accounts never run in the evening, and vice versa.

---

## 2. Shift Pools & Cycle Architecture

| Diurnal Window | Time Slots | Shift Pool | Day 0 (Day 1) | Day 1 (Day 2) | Day 2 (Day 3) | Day 3 (Day 4 - Rest) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ca 1 (Sáng)** | 06:00 & 08:00 | **Pool {Row 1, Row 2, Row 7}** | Rank 1 (Healthiest) | Rank 2 | Rank 3 (Remaining) | Dynamic Funnel |
| **Ca 2 (Trưa)** | 12:00 & 14:00 | **Pool {Row 3, Row 4, Row 8}** | Rank 1 (Healthiest) | Rank 2 | Rank 3 (Remaining) | Dynamic Funnel |
| **Ca 3 (Tối)** | 18:00 & 20:00 | **Pool {Row 5, Row 6}** | Rank 1 (Healthiest) | Rank 2 (Remaining) | Dynamic Funnel | Dynamic Funnel |

---

## 3. Core Invariants

1. **Zero Starvation (100% 8-Row Coverage)**:
   - Over the first 3 days of each 4-day cycle (Day 0, 1, 2), each machine runs all candidate rows in its pool without repetition.
   - Day 0 picks Rank 1; Day 1 picks Rank 2 from remaining unrun rows; Day 2 picks the final remaining row.
   - Across 3 days, 100% of the 8 rows across all 160 machines are fed before Day 3 rest.
2. **"S2 Bám S1" (100% Session 2 Sticking)**:
   - In any given shift, Session 2 (e.g. 08:00, 14:00, 20:00) MUST stick 100% to the exact row selected and run by Session 1 (06:00, 12:00, 18:00) on that machine.
   - Preserves session continuity and prevents rapid profile swapping within the same shift window.
3. **Atomic State & Cycle Rollover (`shift_pool_cycle_state.json`)**:
   - `today_shift_sessions[ca][machine]`: records the row picked in Session 1 for Session 2 to stick. Reset daily.
   - `cycle_history[ca][machine]`: records rows executed within current `cycle_idx`. Reset atomically when `cycle_idx` increments.
4. **Health Ranking Hierarchy in Pool**:
   - **Tier 1 (+100,000 pts):** Viral / Boosted (`is_account_boosted = True`) -> Immediate priority to ride algorithm waves.
   - **Tier 2 (+1,000 pts + video_count):** Clean accounts without follow cooldown (`_is_account_follow_cooldown = False`).
   - **Tier 3 (-10,000 pts):** Jailed / cooling-down accounts -> Ran last in the pool or healed in rest sessions.

---

## 4. Watchdog & Telegram Report Formatting

When running in Shift Pool or Dynamic mode (`active_row <= 0`):
- **Header Convention:** CANNOT display a static single row (e.g. `(Row 1)` or `(Row 0)`). Must display the active pool:
  - Ca 1: `📊 [TIKTOK NUÔI ACC] Ca 1 (Sáng) hoàn tất (Pool {1, 2, 7})`
  - Ca 2: `📊 [TIKTOK NUÔI ACC] Ca 2 (Trưa) hoàn tất (Pool {3, 4, 8})`
  - Ca 3: `📊 [TIKTOK NUÔI ACC] Ca 3 (Tối) hoàn tất (Pool {5, 6})`
  - Rest Day: `📊 [TIKTOK NUÔI ACC] Ca X hoàn tất (Dưỡng Sinh)`
- **Per-Machine Breakdown:** Machine entries in follow, upload, and reconciliation blocks must identify both slot and username:
  `M{m} [Tik X] (@{username})` so operators can immediately see slot distribution across the farm.
