# Follow-failed clean-exit contract

## Trigger

A `FOLLOW_FAILED` result is emitted only after Path B verifies that the target profile still shows `Follow`/`Follow lại` after the row-level follow action. This is a confirmed TikTok follow release, not a generic runner failure.

## Required behavior

1. Persist the per-account/per-day `follow_failed` cooldown state.
2. Stop the current follow session immediately; do not attempt another target or another anchor.
3. In all runner flows (`mode2_follow_followers.py` follower loop, `mode1_search_follow.py`, and `follow_engine.py`), ensure `res.status = STATE_FOLLOW_FAILED`, `res.failed = False`, `res.follow_failed = True`, and loop flag `failed = False`. Never set `res.failed = True` on clean shadow-drop / rate-limit detection.
4. Close TikTok / recent apps through the runner's canonical cleanup method (`cleanup_after_result` calling `close_all_recent_apps`).
5. Treat the cleaned `FOLLOW_FAILED` result as a normal, handled business outcome: exit code `0`, no Telegram "DỪNG PHIÊN"/"GIỮ HIỆN TRƯỜNG" alert, and no retained incident lock.
6. Feed sessions later on the same logical day skip the follow hook for that account and continue only with their allowed non-follow work.

## Alert boundary and parent-hook contract

Do not suppress real technical failures. Alert/retain the scene for `CLEANUP_FAILED`, `MANUAL_REVIEW`, timeout, malformed result, subprocess failure, or any status other than a clean `FOLLOW_FAILED`. A `follow_failed: true` flag alone is not enough to classify the result as clean; require `status == "FOLLOW_FAILED"` and a successful subprocess/cleanup path.

In the parent feed session (`_run_follow_hook` in `multi_machine_feed_session.py`), follow-hook alert suppression and state recording are strictly governed by:
- **Strict `is_clean_follow_failed` predicate:**
  `proc.returncode == 0 and status == "FOLLOW_FAILED" and raw_follow_failed is True and is_strict_zero_failed`
  where `is_strict_zero_failed` requires raw `failed` to be boolean `False` or exact non-negative integer `0`. Any negative number (e.g. `failed = -1`), float (`0.0`), or non-integer type is normalized to `failed = 1` and triggers an alert (fail-closed).
- **Result state flags:**
  `result["follow_failed"]` is set to `True` ONLY when `is_clean_follow_failed` is satisfied. For all technical errors, cleanup failures, timeouts, and unhandled crashes, `result["follow_failed"]` MUST remain `False` so invalid runs do not activate false cooldowns.
- **Preservation of integer failure counts:**
  `result["failed"]` preserves the exact integer count (e.g. `failed = 3` remains `3`, `failed = True` becomes `1`, `failed = False` becomes `0`).
- **Atomic and schema-safe parsing:**
  Validate types into local variables (`raw_status: str`, `followed: list | int`, `skipped: list`, `failed_ids: list`, `details: dict`) before assigning to `result`. Malformed JSON candidate lines or schema-invalid dictionaries must be skipped to allow reading a subsequent valid terminal line.
- **Inconsistent contract detection:**
  A payload with `status == "OK"` but `follow_failed is True` is a contract violation. The parent hook sets `has_contract_error = True`, forces `follow_failed = False`, preserves `failed = 0`, and fires a Telegram alert.
- **Comprehensive timeout and deadline alerts:**
  All four timeout/deadline paths must explicitly fire `send_farm_machine_alert` with `status_text="GIỮ HIỆN TRƯỜNG FOLLOW TIMEOUT"`, `failed = 1`, and `follow_failed = False`:
  1. `follow-hard-deadline-before-start` (deadline <= 0 at function entry).
  2. `follow-hard-deadline-before-subprocess` (deadline <= 0 immediately before launching the child subprocess).
  3. `TimeoutExpired` exception during subprocess execution (both non-fenced and fenced watchdog states).
  4. `follow-hard-deadline-after-run` (deadline <= 0 after subprocess returns).

## Causal state preservation on cleanup failure

When cleanup fails after a `FOLLOW_FAILED` outcome (e.g. `close_all_recent_apps` raises an exception or returns `False`):
- Promote status to `CLEANUP_FAILED`.
- Mark `failed = True` and emit exit code `1` (fail-closed, triggers farm alert and incident lock retention).
- **CRITICAL:** Preserve `follow_failed = True` in both the result object and `_result_payload`. Never wipe `follow_failed` to `False` on `CLEANUP_FAILED`. Downstream orchestrators and state reconcilers require the `follow_failed` flag to enforce cooldowns and account safety even when the terminal app cleanup encountered a transport/infrastructure error.

## Test matrix

- Clean `FOLLOW_FAILED` + cleanup succeeds: app cleanup called, `follow_failed=true`, `failed=false`, exit `0`, alert not called.
- `CLEANUP_FAILED` after a release: exit non-zero (1), `failed=true`, `follow_failed=true` preserved, alert called.
- `CLEANUP_FAILED` after `OK`: exit non-zero (1), `failed=true`, `follow_failed=false`, alert called.
- `MANUAL_REVIEW`/timeout/config error: unchanged fail-closed alert behavior.
- Normal `OK`: cleanup still runs and returns `0`.

This detail came from the operator correction that a confirmed follow release should simply exit the app and stop, rather than be presented as an incident alert.
