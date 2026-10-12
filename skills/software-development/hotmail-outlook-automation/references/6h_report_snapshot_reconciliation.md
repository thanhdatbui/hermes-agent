# 6H Lifecycle Report Snapshot Reconciliation

## Why this matters
A 6-hour lifecycle report is a point-in-time snapshot. The supervisor may process more profiles after the report is generated, so a later read of the canonical state can legitimately contain new BLOCKED entries. Do not silently treat the delivered report as current state.

## Reconciliation procedure
1. Record the report/job generation time from the scheduler metadata when available.
2. Read the canonical Kibe and Admin supervisor state files directly; do not infer current counts from the Telegram text alone.
3. Recompute BLOCKED as `status in {BLOCKED, FAILED, ERROR, QUARANTINE}` and split by farm, stage, and status.
4. Compare each newly observed blocked profile's `updated_at` to the report snapshot time. Attribute only entries updated after the snapshot as post-report delta.
5. Inspect `last_result`, history, and available artifacts before assigning a cause. A bare `status=FAILED` is insufficient evidence for claiming Microsoft service error, OTP rate-limit, or missing recovery data.
6. Keep fail-closed behavior: do not bulk reset or retry BLOCKED/QUARANTINE profiles. Reopen only after per-profile cause, cooldown, and required recovery/security data are verified.

## Reporting style
Lead with deltas and actions, not a verbatim restatement of every metric. Explicitly call out report-vs-live-state mismatches and the evidence for any post-report additions. If the error payload is absent, say the cause is unclassified rather than guessing.

## Two Distinct Reporting Streams for Hotmail
1. **GPM PC Lifecycle (`hotmail-gpm-lifecycle-6h-report`, job `61570a1e37b1` → `telegram:-5583559484`)**:
   - Scope: Hotmail accounts in GPMLogin browser profiles on PC (`HOTMAIL_LOGIN` → `CHATGPT_REG` → `WAIT_7D` → `CHANGE_INFO` → `DONE`).
   - Reporting cadence: Every 6 hours (`0 */6 * * *`).
   - Stage visibility: In newer revisions, `HOTMAIL_LOGIN` is aggregated or suppressed from top headline blocks when virtually all farm accounts have completed it, surfacing primarily when accounts hit `BLOCKED` or `QUARANTINE`.
2. **Physical Phone Farm Outlook App (`post_noon_chain_watchdog` → `telegram:-5373649734` & `daily-tiktok-farm-tracker`)**:
   - Scope: Hotmail/Outlook accounts logged into the Outlook Android app on physical farm devices (`app_logged_in = 1` in `gmail_clean_v2.xlsx`).
   - Reporting cadence: Post-noon shifts (14:00–18:00) and 07:00 daily farm tracker.
   - When asked where "tiến độ login hotmail" is reported, distinguish GPM PC lifecycle vs physical phone farm Outlook app.

## Farm Admin (M201-280) vs Farm Kibe (M1-80) GPM Lifecycle Discrepancies
- **Why Admin skips `HOTMAIL_LOGIN`**: In `batch_gpm_5profiles_supervisor.py`, `initial_stage = "CHATGPT_REG" if has_token else "HOTMAIL_LOGIN"`. Since 681/682 accounts in Admin's `gmail_clean_v2.xlsx` already have OAuth tokens (Col 9), Admin accounts bypass browser login on GPM and directly use Microsoft Graph API to extract verification OTPs. They jump directly to `CHATGPT_REG`.
- **Why Admin ChatGPT Reg paces at 28/day**: Farm Admin only has 28 distinct Mikrotik proxy ports (`10008`–`10035`) shared across 80 machines. The supervisor enforces a strict 24h cooldown per proxy port for the same operation (`ip_action_history[port][stage]`). Thus, Admin can only process 28 accounts/day. In reports showing e.g. 84/620 (28 x 3 days) with 535 pending, the remaining accounts are NOT broken; they are safely waiting for the 24h per-IP cooldown window to roll over.

## Evidence pattern from the lifecycle farm
A report showing 51 Kibe BLOCKED was followed by a live state showing 53: the canonical state had 52 `CHANGE_INFO` BLOCKED and 1 `HOTMAIL_LOGIN` QUARANTINE, with two profiles' `updated_at` values after the report snapshot. This is the expected way to explain a stale report without rewriting historical telemetry.
