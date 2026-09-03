# Canary argument contract — feed-session-smoke vs multi-machine-feed-session (2026-09-03)

Lesson from Máy 74 closeout: the two runner modes take DIFFERENT targeting flags.
Guessing one mode's flags on the other wastes turns on `CONFIG_ERROR` loops.

- `feed-session-smoke` (single machine): `--device <serial> --account <name> --mode feed-session-smoke --max-swipes 2 --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --cleanup-on-stop`. `--device-serial` is NOT a valid flag; bare `--device` without `--machine` may report `machine None is locked`. `--full-scope-takeover` is REJECTED here (multi-machine only).
- `multi-machine-feed-session` (fleet/cron): `--mode multi-machine-feed-session --machines 74 --account-workbook <path> --account-row-index <N> ... --full-scope-takeover`. Requires BOTH `--account-workbook` and `--account-row-index` (`--account-row-index 0` = resolver auto-pick; an explicit Excel row number like 440 may fail validation with `account workbook does not have valid row 440 for machine 74` — use 0 first).
- Lock check before canary: if output says `machine 74 is locked by tiktok-luot nuoi acc (pid ...)`, verify owner live (`tasklist`, process CommandLine) — a live cron holding 74 machines means `BLOCKED_AT_GATE_0_LOCKED_BY_LIVE_CRON`, not a kill/takeover target.
- Failure-stage reading: `status: config-error` + `stop_reason: multi-machine-feed-session requires --account-workbook` (or row validation) = argument problem, NOT a device/UI/popup failure. Read `.ai-runs/<ts>/summary.txt` (`stop_reason`, `multi_machine_summary`) before concluding.
