# Shift Budget Cap and Session 2 Drop Prevention (Optimistic UI & Rate-Limit Defense)

## Root Cause: Why Session 2 (P2) Dropped on Follow #2
In 2-session shifts (e.g. Session 1 at 06:00, Session 2 at 08:00), recovering/probation accounts (`probation_tier1`, `probation_tier2`) suffered repeated follow drops (`FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`) at the 2nd target in Session 2.

### The Mechanics:
1. **TikTok Sliding Window & Daily Rate Limit:**
   - Accounts under recovery/probation have low Inbound Trust with strict daily and hourly rate limits (~4-5 follows/day for Tier 1, ~8 follows/day for Tier 2).
   - In Session 1, `session_budget()` picked a random target (2-4 follows) and executed all of them. `budget_used` reached 3 or 4.
   - In Session 2 (2 hours later), `session_budget()` previously re-rolled another 2-4 follows without checking `budget_used` today.
   - When attempting the 1st follow in P2, the account hit 5 follows (just barely allowed by TikTok's 2h decay window).
   - When attempting the 2nd follow in P2 (total 6 follows), TikTok server silently rejected the follow.
2. **Path B Verification (Optimistic UI Trap):**
   - TikTok UI optimistically toggles the follow button to "Đang follow" in the list view.
   - The follow engine verifies actual state by opening the target's Profile page. On profile view, the button reverted to red ("Follow") because TikTok's backend silently dropped it.
   - The engine correctly caught the drop, marked `set_follow_failed()`, incremented `fail_streak`, and locked the account into a 3 to 15-day progressive cooldown.

## Solution Architecture: Hard Shift/Daily Budget Cap
In `follow_runner/core/follow_state.py` (`_determine_budget_tier`):
- For `probation_tier1` (`clean_days < tier1_threshold`): Daily/Shift cap is strictly **4**.
- For `probation_tier2` (`clean_days >= tier1_threshold`): Daily/Shift cap is strictly **8**.
- `remaining = max(0, cap - int(self._data.get("budget_used", 0)))`.
- If `remaining <= 0`, return `0` immediately (`safe-skip`). The runner skips follow actions and stays in pure feed, preserving `clean_days`.
- If `remaining > 0`, return `min(remaining, random_target)`.
- Full (graduated) accounts continue to use the standard session budget (10-15 follows) without daily probation clamping.

## Dual-Answer / Architectural Guidance: 4 Shifts vs Device Fingerprinting
- **Account-Level:** Each account runs only 1 shift every 4 days (40 mins/96h), exhibiting natural human behavior.
- **Device-Level (Advisor Sol Insight):** Running 4 shifts/day (6h, 8h, 12h, 14h, 18h, 20h, 0h) increases the hardware activity footprint and device correlation across accounts. Running Ca 0h (night shift) should be evaluated at the Device/IP layer and tested on a small pilot group before fleet-wide rollout.
