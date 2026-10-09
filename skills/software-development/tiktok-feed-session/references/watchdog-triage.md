# Watchdog Session Triage & Reporting Guide

## Overview
When a TikTok feed-session watchdog fires with mixed outcomes (success, fail, organic-rest, follow reconciliation mismatch, upload hook failures), the coordinator must perform structured, evidence-backed triage rather than treating it as a generic failure.

## 1. Trace the Artifacts Directly (O(1))
Do not grep or walk the whole disk. Find the run directory under the cluster runtime:
- `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<row>-<HHMMSS>/<run_id>/`
- `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/row-<row>-<HHMMSS>/<run_id>/`

Read:
1. `run_manifest.json`: Parse `multi_machine_summary` for per-machine `final_status` and `stop_reason`.
2. `summary.txt`: Check aggregate counts (`blocked-proxy-vpn`, `manual-needed`, `failed`, `config-error`, `success`).
3. `upload_result.json` per machine: Identify exact upload failure reasons (`ACQUIRE_LOCKS`, `organic-rest-day-upload-disabled`, `missing_account_id`).
4. `follow_result.json` per machine: Identify follow outcomes (`FOLLOW_FAILED` vs `follow-released-daily-cooldown` vs `MANUAL_REVIEW`).

## 2. Separate Outcome Classes
- **Organic Rest (~33%):** Normal policy behavior (pure feed, no follow, no upload). Never count as failures or alert triggers.
- **Under-10-video Skip:** Account safety rule. Not an error.
- **Device-lock Contention / ACQUIRE_LOCKS:** Another process (or previous unreleased lock) holds the device lease. Requires lock inspection/reaping, not script rewriting.
- **ADB Offline / Disconnected:** Hardware or USB/IP bridge failure. Inspect using `inspect_machine.py <N>`.
- **Manual-Needed UI Checkpoint:** Splash ad, profile mismatch, or account switcher missing expected username.

## 3. Account Workbook Mapping (@username)
Per Taadaa Farm invariant, reporting by machine number alone is prohibited. Always resolve the machine number to `@username`:
- Workbook paths:
  - Kibe: `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`
  - Admin: `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`
- Slot index = `account_row - 1`. Match machine ID in column A (1-based index 0), extract username from column C (1-based index 2).
- Output format: `M<machine_id> (@<username>): <reason>`.

## 4. Reconcile Web Following vs Script Following
When watchdog reports a mismatch between script-reported follows and Web profile delta:
- Extract snapshot history from `D:/Taadaa/data/tiktok_tracker.db` table `snapshots`.
- Calculate `delta = latest_following - baseline_following`.
- If `delta != script_reported`, highlight the discrepancy per account.
- Note whether the mismatch indicates delayed TikTok follower counters, external follows, or script reporting bugs.

## 5. Live Device Inspection Guardrails
- If inspecting a failed machine, use: `python D:/Taadaa/tools/inspect_machine.py <N>`.
- Do not conclude root cause from a post-session state (e.g. LauncherActivity / Screen OFF), as cleanup (`cleanup_close_all`) runs on completion.
