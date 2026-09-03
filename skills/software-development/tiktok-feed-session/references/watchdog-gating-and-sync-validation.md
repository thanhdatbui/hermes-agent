# Watchdog Gating & Workbook Sync Validation Rules

## 1. Watchdog Reporting Gating (`can_report_session`)
- **Premature reporting prevention**: Watchdog must NEVER report partial/early machine results while background runners (`powershell` / `python multi_machine_feed_session` / `run_follow`) are actively executing (`runner_busy: True`).
- **Gating condition**: Even if the current time exceeds the window end (`now_hm >= window_end_hm`), `can_report_session` must return `False` if `runner_busy` is `True`.
- **Completion handling**: When runner workers finish, `runner_busy` becomes `False`. The watchdog then evaluates `(completed_expected_count >= expected_count) or (now_hm >= window_end_hm)` to report the complete, multi-run merged session.

## 2. Process Timeout & Stuck-Lock Protections
- **Worker hard timeout**: Multi-machine feed runners enforce bounded execution (`_worker_hard_timeout_seconds` ~20-25m per device/batch), cutting off hanging ADB/subprocesses automatically with `hard outer watchdog deadline exceeded`.
- **Dead owner cleanup**: `scripts/reap-dead-owner-locks.py` runs periodically to reclaim locks when parent PIDs have exited.
- **Fail-safe reporting**: Once workers terminate, watchdog resumes reporting without deadlocks.

## 3. Workbook Sync Nick Validation (`is_valid_tiktok_id`)
- **One-way sync contract**: `scripts/sync-tik-workbooks.py` syncs IDs from `taikhoan_dat_v2` into `Tik1..Tik6.xlsx`.
- **Validation rule**: Clean only true placeholders (`none`, `null`, `ghjfghj`, `http://`, `https://`, pure numbers, start/end dots).
- **Pitfall**: Never blacklist valid user handle strings or prefixes (e.g. `vo.my`, `ngomai.ly`), as that wipes valid accounts in `Tik1..Tik6.xlsx` into `MISSING_ID`.
- **Regex pattern**: Use `^[a-zA-Z0-9_.]{2,24}$` (reject leading/trailing dot and URLs with `/`).

## 4. Follow Zero-Follow Classification & Hybrid Flow
- **Module 2 -> Module 1 Hybrid**: Module 2 searches up to 3 anchors. If an anchor has 0 following or is already fully followed, it advances to the next anchor. If quota remains unfilled, it falls back to Module 1 search-follow.
- **Status OK with 0 follow**: When daily budget is full (`budget_used >= 40`) or no valid follow target was found, the hook finishes with `status: "OK", followed: []`. Watchdog MUST NOT misclassify this clean termination as a script error.
- **Daily Follow Cooldown**: If a follow is released (`FOLLOW_FAILED` confirmed after reload), `follow-released-daily-cooldown` halts follow for the remainder of the day, keeping the account in feed-only mode to prevent shadow ban.
