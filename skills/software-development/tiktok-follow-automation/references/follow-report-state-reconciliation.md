# Follow report/state reconciliation

Use this whenever a watchdog message contains both Feed and Follow sections, or when the operator asks whether released follows were blocked for the day.

## Interpret the report correctly

- `Lướt Feed -> Fail` is a feed/session failure. It is **not** evidence that the machine was follow-released.
- `Follow chéo -> Nhả follow` is the authoritative report list for follow-release events.
- `Follow chéo -> Lỗi` is a follow-run failure and must remain distinct from `Nhả follow`.
- Confirm the row from each `follow_result.json` (`row` / `account_row_index`); do not infer row from the feed-failure list.

## Evidence-first reconciliation

1. Resolve the exact run directory from the watchdog timestamp and row/session label.
2. Enumerate `machines/machine_*/**/follow_result.json` for that run.
3. Parse each result and produce separate sets for:
   - `status == FOLLOW_FAILED` from the explicit post-tap/post-refresh verifier (release detected); do not treat `follow_failed == true` as sufficient when legacy artifacts may have overloaded that flag with subprocess exit errors;
   - `status` equal to the runner's error/timeout states;
   - successful follow results and followed-count totals.
4. For every release-detected machine, inspect the state file used by the runner:
   `D:/Taadaa/tiktok-follow/runs/state/follow_state_<machine>_row_<row>.json`, with the legacy machine-only fallback only if the row-specific file is absent.
5. Evaluate the actual daily gate, not file existence:
   - `follow_failed_date == today`, or
   - `follow_failed == true` and `budget_date == today`.
6. Report two independent counts: release results found vs state entries that currently block Follow today. If they differ, the daily state-write/propagation path is incomplete; do not claim the block is active.

## Required safety conclusion

A valid implementation may skip only the affected nick/row for the remainder of the day; it must not disable Follow for every account on the machine or every row. For accounts with no release state today, the safe conclusion is `BLOCK_STATE_NOT_CONFIRMED`, not “already blocked”.

## Pre-flight cohort session follow evaluation (upcoming session audit)

When determining how many accounts/nicks will execute Follow in an upcoming cron session:
1. **Manifest & Cohort resolution:** Parse the active assignment manifest (`D:/Taadaa/runtime/kibe/cron-state/manifests/<date>/assignment-*.json` or `ACTIVE.json`) for the target session index and slot time.
2. **5-Gate Follow Preflight Pipeline:**
   - **Gate 1 (Device Lock):** Machine has an active lock in `~/.codex/device-locks/` (`status == "blocked"` or `"locked"`, TTL < 2h) -> skip session/follow.
   - **Gate 2 (Zero-Video Policy):** Account has `video_count <= 0` in workbook -> skip follow (`zero-video-follow-disabled`).
   - **Gate 3 (Warmup Phase Policy):** Row index in (3, 4, 5, 6) during 14-day warmup -> skip follow (`tik{row}-warmup-feed-only`).
   - **Gate 4 (Follow-Release Daily Cooldown):** Account row state file `follow_state_{machine}_row_{row}.json` satisfies `follow_failed_date == today` or (`follow_failed == True` and `budget_date == today`) -> skip follow (`follow-released-daily-cooldown`).
   - **Gate 5 (Daily Budget Exhaustion):** `budget_used >= budget_per_day` (configured in `follow_runner/config.example.yaml` / `core/config.py`, e.g. 30 or 40) for today's date -> skip follow (daily limit reached). If the operator requests raising the daily limit mid-day (e.g. 30 -> 40), accounts that were previously capped immediately regain remaining slots (`budget_remaining = budget_per_day - budget_used`) without resetting or wiping state files.
3. **Follow-Eligible Accounts:** Accounts passing all 5 gates proceed with per-session budget (4–6 follows per session).

## Compact evidence table

| Claim | Required evidence |
|---|---|
| Feed failed | Feed `summary.txt` / watchdog Feed Fail list |
| Follow was released | `follow_result.json` with `follow_failed: true` or watchdog Nhả follow list |
| Correct row | `follow_result.json.row` plus exact run path |
| Blocked for today | row-specific `follow_state_*.json` satisfying the daily predicate |
| Only that nick is skipped | runner lookup includes machine + `account_row_index` and returns `status: skipped` |

Do not merge these claims based on machine number alone. A machine can have a Feed failure, a Follow release, a Follow timeout, and a daily cooldown state as separate facts.
