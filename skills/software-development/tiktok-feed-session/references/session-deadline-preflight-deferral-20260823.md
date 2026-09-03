# Session deadline preflight deferral (2026-08-23)

## Change
Moved per-device session deadline assignment in `_run_child` (`python_runner/flows/multi_machine_feed_session.py`):

REMOVED from child-config setup (was before `_build_child_context`, ~line 1407):
```python
timeout_seconds = float(ctx.config.get("_device_timeout_seconds") or _cfg_subdict(ctx.config, "timeouts").get("device_seconds", DEFAULT_DEVICE_TIMEOUT_SECONDS))
child_config["_deadline_monotonic"] = time.monotonic() + timeout_seconds
```

ADDED in the nested preflight-success branch (~line 1449), immediately before `result = feed_session_smoke(child_ctx)`:
```python
# after validation.status == ExitStatus.SUCCESS AND prepare.status == ExitStatus.SUCCESS
timeout_seconds = float(...)  # same precedence: _device_timeout_seconds -> timeouts.device_seconds -> DEFAULT_DEVICE_TIMEOUT_SECONDS (1500)
child_config["_deadline_monotonic"] = time.monotonic() + timeout_seconds
```

Effect: ADB validation + `prepare_tiktok_for_smoke` wall time no longer consume the 1500 s session budget; preflight failure means NO `_deadline_monotonic` key exists. Consumers untouched (`core/deadline.py::ensure_run_plan_deadline`, feed_swipe_smoke watch-delay check). Note `_build_child_context` passes the same `child_config` object into `child_ctx.config`, so late assignment is visible to `feed_session_smoke`.

## Regression tests added (MultiMachineFeedSessionTests, test_multi_machine_feed_session.py)
- `test_session_deadline_starts_only_after_validation_and_prepare`: `_device_timeout_seconds=900`; fake_prepare records `child_ctx.config.get("_deadline_monotonic")` (must be `None` during prepare) plus `time.monotonic()` finish stamp; fake_feed records deadline + start stamp. Asserts `deadline_at_feed > prepare_finished_at` and remaining budget in `(840, 900]` — proving preflight time is not deducted.
- `test_no_session_deadline_when_prepare_preflight_fails`: fake_prepare returns FAIL and records config deadline (must be `None`); asserts FAIL result, `feed_mock.assert_not_called()`, no deadline ever assigned.

## Vacuous-pass pitfall (hit during RED)
First version put `assert "_deadline_monotonic" not in child_ctx.config` INSIDE fake_prepare. Under the OLD buggy code the assert raised AssertionError → the generic `except Exception` wrapped it into `final_status="failed"` → the test's own expectations (FAIL result, feed not called) still held → test PASSED while the bug existed. Fix: observe into an `observed` dict inside the mock; assert outside the `with` block. Rule: never assert expected-failure conditions inside a side_effect.

## Verification transcript
- RED (pre-fix): both new tests failed correctly — `AssertionError: 183436.296 is not None` on `assertIsNone(observed["deadline_during_prepare"])`.
- GREEN focused (5): new 2 + `test_child_honors_per_device_deadline_and_finalizes_summary` + `test_execute_prepares_tiktok_before_feed_baseline` + `test_execute_stops_before_baseline_when_startup_prepare_fails` → `5 passed in 4.61s`.
- Full file: `54 passed, 3 failed` — the 3 failures are pre-existing (proof below).
- Command shape: `PYTHONPATH=".:/d/Taadaa/tiktok-luot nuoi acc/python_runner" python -B -m pytest -q -p no:cacheprovider python_runner/tests/test_multi_machine_feed_session.py`
- `compileall` on the flow file OK; `git diff --check` clean.

## Pre-existing failure proof via throwaway worktree
Failures: `test_incomplete_lock_alias_identity_is_deferred`, `test_normal_schedule_rechecks_handoff_before_child_submission`, `test_normal_schedule_skips_prior_handoff_when_lock_files_are_missing` — all fully mock `_run_child`; symptom `[ALERT] worker returned unexpected result type: MagicMock` then `'failed' != 'skipped-device-locked'`.
Proof procedure (zero risk to dirty worktree):
```bash
cd "/d/Taadaa/tiktok-luot nuoi acc"
git worktree add "D:\\Taadaa\\_headcheck_tmp" HEAD
cd "/d/Taadaa/_headcheck_tmp"
PYTHONPATH=".:/d/Taadaa/_headcheck_tmp/python_runner" python -B -m pytest -q -p no:cacheprovider <suspect tests>   # identical failures => pre-existing
cd "/d/Taadaa/tiktok-luot nuoi acc" && git worktree remove "D:\\Taadaa\\_headcheck_tmp" --force && git worktree list
```
Quirk: passing MSYS-style `/d/Taadaa/_tmp` made git create the worktree at `D:/d/Taadaa/_tmp`; always pass Windows-style quoted paths to `git worktree add/remove`.

## Concurrent-worker observation
Mid-session another worker staged changes to `python_runner/flows/feed_swipe_smoke.py` + `tests/test_feed_swipe_smoke.py` (status flipped `M` → `MM`). Outside this task's contract; preserved unstaged/unstaged-boundary intact and reported separately per the closeout rule. Re-check `git status --short` immediately before reporting completion on shared worktrees.
