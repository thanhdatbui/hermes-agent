# Schedule Redesign: 4Ca Simplification (10/09/2026)

## Context
User reported: "Ủa hôm bữa t tinh giản 1 lần r chạy 1 hồi con chó nào ms thêm cái cohort vào v" — previous simplification was reverted by a subagent adding picker/cohort/manifest layers.

## Problem
- Old system: 4Ca x 2Phiên = 8 windows/day, picker/cohort/manifest over-engineering
- Cohort validation hard-coded `block not in (1,2,3)` → rejected Block 4 (Ca 4/Row 8)
- Entire farm died silently (`active manifest has no valid cohort`)

## Solution Applied

### 1. `tiktok_runner.py` (Hermes scripts) — Simplified to ~280 lines
- Removed all picker/cohort/manifest imports
- Schedule logic: time-of-day → Row mapping
  - 00h → Row 7/8 (Ca đêm)
  - 06h → Row 1/2 (Ca sáng)  
  - 12h → Row 3/4 (Ca trưa)
  - 18h → Row 5/6 (Ca tối)
  - 01-05h = dead zone
- Artifact root: `D:\Taadaa\runtime\kibe\live\{date}\row-{row}-{HHMMSS}`
- Dedup via simple state file `runner_simple_state.json`

### 2. `feed_session_watchdog.py` — Collapsed 8 windows → 4 Ca
- SESSION_WINDOWS: 4 entries covering full Ca duration
- Removed `phien` key from window dicts
- Fixed boundary: Ca 4 uses [00:00, 06:00), Ca 1 uses [06:00, 12:00)
- Removed all `win["phien"]` references in upload classification

### 3. Core scripts cleanup (commit 7120fab)
- `run_tiktok.py`: removed `--cohort-artifact`, `--assignment-manifest` args
- `multi_machine_feed_session.py`: gutted `_apply_cohort_identity()`, removed `load_cohort_plan` fallbacks

### 4. `cohort.py` fix (commit 8155776)
- `if block not in (1, 2, 3, 4)` — accept Block 4

## Key Principle
**Time-of-day drives schedule, not manifest/cohort picker.** Runner spawns PS1 directly against `taikhoan_run_safe.xlsx`. Watchdog scans artifacts by time window.

## Files Modified
- `C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py` (rewritten)
- `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py` (patched)
- `python_runner/hermes_cron/cohort.py` (1 line fix)
- `python_runner/run_tiktok.py` (removed args)
- `python_runner/flows/multi_machine_feed_session.py` (removed cohort logic)

## Cron Jobs Active
- `phase9-runner-tiktok-feed` (*/15): runs tiktok_runner.py
- `tiktok-feed-session-watchdog` (*/5): reports per Ca completion

## Pitfall to Avoid
Never re-introduce picker/cohort/manifest for daily feed scheduling. The 4Ca schedule is deterministic by clock time.