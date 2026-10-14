# Continuous Rolling Avatar Operations & Anti-False-Yield Reporting (2026-10-15)

## 1. Context: 3-Ca Farm Schedule (Bỏ Ca 4 Đêm)
- TikTok feed schedule is now strictly 3 Ca x 2 Sessions (06:00, 12:00, 18:00).
- Night Ca 4 (00:00 - 05:30) is completely abolished.
- This unlocks a continuous 6.5-hour idle window ban đêm: `21:30 → 04:00` (before 04:00 cache clear).
- Farm also has daytime idle windows: `09:30 → 11:45` and `15:30 → 17:45`.

## 2. Pitfall: Legacy 23:45 Evening Truncation & False "Nhường Lịch Nuôi"
- **Legacy truncation:** `is_after_evening_window` triggered at 23:45, stopping batch launches for the entire night and forcing an incomplete report.
- **Reporting bug (Slot vs Distinct Machine):**
  - Summing `unuploaded` across Tik 1..8 yields unuploaded account slots (`tot_miss`), NOT unique machines.
  - Example: M10 and M30 offline in 6 Tiks each = 12 slots, but only 2 physical machines.
- **Reporting bug (False "Nhường lịch"):**
  - Unconditionally labeling `tot_miss` as "Bỏ qua an toàn: {tot_miss} máy (nhường lịch nuôi TikTok / lock tiến trình khác)" falsely blamed the feed schedule during midnight hours when no feed ca was running, while obscuring genuine errors (DEVICE_OFFLINE, SWITCHER_FAILED).

## 3. Standard Continuous Rolling Protocol
- Run continuous rolling batches across all farm idle windows until 100% DONE.
- Stop conditions:
  * Only when feed runner is actively running (`is_feed_runner_active()`).
  * Within 30 minutes before next scheduled feed ca.
  * During 04:00 - 04:45 daily cache-clear window.
- Periodic cadence reporting (every 6h: 00:00, 06:00, 12:00, 18:00 or 12h) to avoid fragmented spam.
- Explicit report breakdown:
  * Total DONE % (accounts / target).
  * New SUCCESS in window.
  * Real Technical Failures (distinct machines grouped by error).
  * Pending Queue (machines waiting for next batch).
  * NEVER claim "nhường lịch nuôi" unless verified active feed lock exists.
