# Farm Cadence & Multi-Layer Jitter Architecture (2026-10-07)

## 1. Farm Operating Realities (160 Machines / 1,280 Accounts)

- **Parallel Execution:** 160 physical machines (Samsung S7 / equivalent) operate concurrently and independently via individual background workers.
- **Alternating Day Parity (Even / Odd Days):**
  - Each machine manages 8 rows (Row 1 to Row 8).
  - **Odd Days (1, 3, 5, 7...):** Runs Odd Rows (Row 1, 3, 5, 7) — 4 accounts/machine. Even rows rest completely (~32–36h continuous rest).
  - **Even Days (2, 4, 6, 8...):** Runs Even Rows (Row 2, 4, 6, 8) — 4 accounts/machine. Odd rows rest completely.
- **4 Ca x 2 Phiên / Day (8 Windows):**
  - **Ca 1 (Morning):** P1 at 06:00 (Feed only) | P2 at 08:00 (Feed + Upload hook) -> Row 1 (odd) / Row 2 (even)
  - **Ca 2 (Noon):** P1 at 12:00 (Feed only) | P2 at 14:00 (Feed + Upload hook) -> Row 3 (odd) / Row 4 (even)
  - **Ca 3 (Evening):** P1 at 18:00 (Feed only) | P2 at 20:00 (Feed + Upload hook) -> Row 5 (odd) / Row 6 (even)
  - **Ca 4 (Night):** P1 at 00:00 (Feed only) | P2 at 01:30 (Feed + Upload hook) -> Row 7 (odd) / Row 8 (even)
- **Device Load & Screen-On Time:**
  - 1 machine runs 4 accounts x 2 sessions = 8 sessions/day.
  - Each session lasts ~7–8 minutes.
  - Total screen-on time per machine: **~60–65 minutes / 24 hours** (~2.7% duty cycle per ca).
  - Machine stays idle > 22 hours/day, preventing thermal throttling or battery swelling on legacy S7 hardware.

---

## 2. Verified 3-Tier Jitter Architecture

### Tier 1 — Cron Window Gate (`tiktok_runner.py`)
- Cron triggers `*/15 * * * *`.
- Checks `_determine_row()` against exact slot keys `(06, 00)`, `(08, 00)`, `(12, 00)`, `(14, 00)`, `(18, 00)`, `(20, 00)`, `(00, 00)`, `(01, 30)`.
- Lightweight filter without overhead.

### Tier 2 — Session Start Jitter (`run-feed-session.ps1` lines 421–430)
- **Code:**
  ```powershell
  $SessionJitterMinSeconds = 60
  $SessionJitterMaxSeconds = 180
  $sessionJitterSec = Get-Random -Minimum 60 -Maximum 181
  Start-Sleep -Seconds $sessionJitterSec
  ```
- **Behavior:** Sleeps randomly 1 to 3 minutes before dispatching any device automation.
- **Safety Boundary:** DO NOT increase beyond 3 minutes. Increasing to 3–5 minutes risks encroaching on watchdog grace period (20 minutes) or overlapping the next session window (especially Ca 4 P1 00:00 -> P2 01:30 gap is only 90 minutes).

### Tier 3 — Machine Order & Stagger (`run-feed-session.ps1` & `multi_machine_feed_session.py`)
- **`-RandomizeMachineOrder`:** Shuffles device list randomly each run, preventing fixed numerical order `M1 -> M2 -> M3`.
- **`-MachineStartStaggerMs "2000,8000"`:** Spawns devices with 2,000ms to 8,000ms randomized interval between each, scattering initial app opens across the timeline.

---

## 3. Micro-Jitter Inside App Session (`feed_swipe_smoke.py`)

- **Swipe Dwell Time:**
  - Fast swipe: 3.0s – 5.0s.
  - Deep Inspect: 8.0s – 12.0s (dwell before natural follow, like rate 48%).
- **Macro Persona vs Micro Jitter Rule:**
  - **Macro (Fixed):** Fix the persona schedule (Row 1 always wakes in morning, Row 7 always wakes at night) to build a consistent behavioral identity.
  - **Micro (Random):** Randomize seconds and minutes within the session window to eliminate bot fingerprints.
