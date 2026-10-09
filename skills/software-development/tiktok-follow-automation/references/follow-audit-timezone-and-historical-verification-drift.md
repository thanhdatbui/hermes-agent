# Audit Timezone Normalization & Historical Verification Drift

## 1. Timezone Normalization Invariant (UTC vs Asia/Ho_Chi_Minh)
- **Problem:** Timestamps in `follow_state_*_row_*.json` are persisted in standard UTC ISO format (e.g., `2026-10-02T23:23:35+00:00`).
- **Pitfall:** Naive string matching on date prefixes (`ts.startswith("2026-10-02")`) causes severe reporting errors:
  - Farm runs occur in morning shifts (06:00 - 08:30 GMT+7).
  - 06:30 AM on Oct 3 GMT+7 corresponds to 23:30 UTC on Oct 2.
  - Naive date slicing incorrectly reports that "Row 1 ran on even day (Oct 2)", violating Parity Lane invariants (Odd days: Rows 1, 3, 5, 7; Even days: Rows 2, 4, 6, 8).
- **Mandatory Audit Rule:**
  - ALWAYS parse ISO timestamps with timezone awareness and convert to `Asia/Ho_Chi_Minh` before grouping by date or checking parity lane compliance:
  ```python
  from datetime import datetime
  from zoneinfo import ZoneInfo
  HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
  dt_local = datetime.fromisoformat(ts).astimezone(HCMC)
  local_date = dt_local.strftime("%Y-%m-%d")
  ```

## 2. Root Cause of High Cooldown Relapse Rate (Historical Verification Drift)
- **Pre-Oct 2 Bug (Commit `c12242d`):**
  - Legacy `verify_follow.py` misidentified profile header stat counter labels (`id/sdn`, `id/shq`, `id/t1i`, `id/t_q` showing `"127 Đã follow"`) as successful follow action button conversions.
  - When TikTok server silently dropped follows (Path B), the bot failed to detect the drop and continued attempting 10–20 follows per session.
  - This repeated firing against an active action block caused TikTok's server-side antispam filter to escalate penalties across ~340+ farm accounts.
- **Post-Oct 2 Reality (Hardened Re-entry Verification):**
  - Commit `c12242d` introduced Natural Re-entry and strict action button whitelist filtering (`id/fds`, `id/ff8`, `id/fo4`, `id/u9f`).
  - True fleet state revealed: ~85–93% of previously penalized accounts relapse immediately on their first follow tap after exiting cooldown.
  - Daily active follow throughput is sustained by a small unpenalized core (~6–8 accounts on Row 1, ~3–4 accounts on Row 2 per active shift).
