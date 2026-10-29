# TikTok Farm Shift-Pool Architecture: 3-Day Cycle & Decoupled State

## Core Operating Principles
1. **3-Day Continuous Cycle (No Day 4)**:
   - Ca 1 (Sáng: 06h, 08h): Pool `{Row 1, Row 2, Row 7}` (3 slots = 3 days).
   - Ca 2 (Trưa: 12h, 14h): Pool `{Row 3, Row 4, Row 8}` (3 slots = 3 days).
   - Ca 3 (Tối: 18h, 20h): Pool `{Row 5, Row 6}` (Day 1 & Day 2) + Slot Dynamic 3-Tier Nurture (Day 3).
   - Day 4 rest day was completely removed. Cycle resets to Day 1 immediately after Day 3.

2. **Per-Ca Decoupled State**:
   - Each shift manages its own state in `cycle_history[ca_key][machine_key]`.
   - The three shifts operate on completely disjoint account pools (`{1,2,7}`, `{3,4,8}`, `{5,6}`).
   - Shift desynchronization (e.g. Ca 1 at Day 3 while Ca 3 at Day 1) is **completely safe and by design**. It prevents cross-shift cascading failures when one shift encounters a network/device fault.

3. **48h Follow Hard Gate (`_is_account_follow_cooldown`)**:
   - Enforces `0.0 <= age_hours <= 48.0` between follow sessions on different calendar days.
   - Even if dynamic selection picks an account, it cannot follow if it has followed within 48h.
   - Natural 3-day shift rotation yields ~72h interval between runs of the same slot, well exceeding the 48h safety floor.
