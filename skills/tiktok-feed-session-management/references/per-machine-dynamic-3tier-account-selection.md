# Per-Machine Dynamic 3-Tier Account Selection Contract

## 1. Context & Motivation
In the 4-day nurture cycle (`Day 0 = Rows 1,3,5`, `Day 1 = Rows 2,4,6`, `Day 2 = Rows 7,8,Dynamic`, `Day 3 = Rest Day 3x Dynamic`), previous implementations attempted to select a single "healing row" farm-wide. This caused severe allocation mismatch:
- Machine A's Slot 2 was trending, but the farm picked Row 4.
- Machine B's Slot 5 was jailed for follow cooldown, but the farm picked Row 3.
- Machine C had all slots healthy, wasting a rest session on an already-aged account.

**The Solution:** Discard farm-wide row locking for dynamic sessions. In dynamic windows (`row_index = 0`), each machine independently inspects all 8 slots in its workbook and resolves the optimal account using a 3-tier funnel.

---

## 2. The 3-Tier Funnel

When `resolve_dynamic_account_for_machine(machine, rows)` executes:

### Tier 1 (Priority 1) — Trending Momentum (`is_account_boosted`)
- **Condition:** Account has rapid follower/heart surge ($\ge 20$ followers or $\ge 50$ hearts) or active viral views in `tiktok_tracker.db` via `flows.account_boost.is_account_boosted()`.
- **Action:** Select slot immediately. Bypasses organic rest (`_upload_in_organic_rest = True`) to upload a fresh video and ride the 24-48h algorithm wave.
- **Guard:** 0 follow (prevents follow rollback penalties while riding viral momentum).

### Tier 2 (Priority 2) — Penalty Healing / Jailed Accounts (`_is_account_follow_cooldown`)
- **Condition:** No slot qualifies for Tier 1, but at least one slot has active `follow_failed` or cooldown in `follow_state_{machine}_row_{r}.json`.
- **Action:** Select the cooling-down slot. Conducts pure feed session (0 follow, 0 upload) to clear penalty flags and recover account trust score.

### Tier 3 (Priority 3) — Young Account Accumulation (`min(video_count)`)
- **Condition:** Machine has no trending and no jailed accounts.
- **Action:** Pick the slot with the lowest `video_count` (prioritizing accounts with $< 10$ videos) to build channel depth.

---

## 3. Invocation & Interface Contract

1. **Row Convention:**
   - `Row = 1..8`: Standard static row shift.
   - `Row = 0`: Dynamic per-machine mode.
2. **PowerShell Launcher (`run-feed-session.ps1`):**
   - Param `$Row` validated as `[ValidateRange(0, 8)]`.
   - When `$Row -eq 0`, passes `--account-row-index 0` to `run_tiktok.py`.
3. **Workbook Selection (`feed_session_workbook.py`):**
   - `select_feed_session_accounts(..., row_index=0)`: For each machine in `machines`, resolves dynamic account via `resolve_dynamic_account_for_machine(machine, rows)`.
   - Filters out blank usernames or string `"none"`.
   - Gracefully handles `video_count = None` (treated as 0/least).
4. **Telemetry & Audit:**
   - Logs `[DYNAMIC_SELECT] machine=<M> tier=<1_boosted|2_jailed|3_youngest> row=<R> user=<U>`.
   - Never fails silently: exception in detector logs warning and falls back to subsequent tier.
