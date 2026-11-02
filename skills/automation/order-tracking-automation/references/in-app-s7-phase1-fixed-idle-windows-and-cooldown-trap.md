# In-App S7 Phase 1 Fixed Idle Windows & Cooldown Trap

## 1. The Dynamic Cooldown Trap (Bẫy Cooldown Động)
- **Problem:** Implementing Phase 1 in-app sync with dynamic elapsed cooldowns (e.g. `now - last_run_ts >= 5.5h` or `6h`) inside a frequent cron schedule (e.g. every 15-30m `*/15 6-22 * * *`) causes fatal cadence drift:
  - If a previous cycle ran late (e.g. 22:47), the next 5.5h window lands at ~04:17.
  - If the cron schedule only spans `6-22`, the 04:17 window is completely skipped.
  - At 06:00 (first morning tick), the system sees `elapsed > 5.5h` and attempts to touch farm phones right as morning feeding shifts start or when devices are in transit.
  - Even worse, it starves mid-morning slots (10:30) because 06:00 resets the 5.5h cooldown to 11:30 (colliding with Ca 2 lunch feeding shift).
- **Hard Rule:** Never use dynamic floating cooldowns for device-touching tasks on phone farms.

---

## 2. Fixed Four Idle Windows Pattern (4 Khung Giờ Rảnh Cố Định)
Phase 1 phone inspection on Samsung S7 MUST strictly bind to fixed farm idle buffer slots between feeding shifts:
1. **04:30 – 05:00:** Post-cache cleanup (04:00), pre-Ca 1 morning feed (06:00).
2. **10:30 – 11:00:** Post-Ca 1 feed, pre-Ca 2 lunch feed (11:35).
3. **16:30 – 17:00:** Post-Ca 2 post-noon chain, pre-Ca 3 evening feed (17:45).
4. **22:30 – 23:00:** Post-Ca 3 feed & avatar, pre-Ca 4 midnight feed (00:00).

---

## 3. Slot-Based Idempotency
- Use slot identity `YYYYMMDD_HH` (e.g. `20261102_16`) stored in persistent state (`order_phase1_sync_state.json` -> `last_run_slot`).
- Within the window (e.g. hour == 16 and minute >= 30), execute Phase 1 once across all pending `NEED_APP_SYNC` orders via parallel workers under `operator_device_lock`.
- Once executed, record `last_run_slot = current_slot_id` so subsequent cron ticks within the same 30m window immediately skip Phase 1 and only execute Phase 2 Web API tracking.
- Outside the 4 fixed windows, Phase 1 is strictly bypassed, leaving S7 phones 100% free for feed runners and battery cooling.
