# Local dev & test pitfalls (python_runner feed-session)

Condensed from a constants-bump task on `multi_machine_feed_session.py`
(`FEED_SESSION_MIN_TOTAL_VIDEOS` 15→10, `FEED_SESSION_MAX_TOTAL_VIDEOS` 30→18).

## Project layout — where the package root actually is
- Repo root: `D:\Taadaa\tiktok-luot nuoi acc\`
- **Importable package root is `python_runner/`** — `flows`, `core`, `automation_core`
  live UNDER it. Pointing `sys.path` at the repo root gives
  `ModuleNotFoundError: No module named 'flows.multi_machine_feed_session'`.
- Test suite lives in `python_runner/tests/` and starts with `import _path_setup`
  (also there). Run pytest **from inside `python_runner/`** or via the venv that
  already has the path configured.

## Running the suite / ad-hoc verification
- Venv interpreter: `D:\Taadaa\python-envs\automation\Scripts\python.exe`
  (pytest next to it). Run full suite:
  `cd D:\Taadaa\tiktok-luot nuoi acc\python_runner && <venv>\Scripts\pytest.exe tests/test_multi_machine_feed_session.py -q`
- Ad-hoc one-off check: write a temp script under
  `C:\Users\Kibe\AppData\Local\Temp\hermes-verify-*.py`, set
  `sys.path.insert(0, r"D:\Taadaa\tiktok-luot nuoi acc\python_runner")` BEFORE
  importing `flows.*`, run with the venv python, then delete it. Flag the result
  explicitly as "ad-hoc verification", not "suite green".

## Tooling gotcha: search_files chokes on spaced Windows paths
`search_files` (ripgrep wrapper) returns
`IO error: The system cannot find the path specified. (os error 3)` for paths
containing spaces like `tiktok-luot nuoi acc`. Workaround: use the terminal
instead — `grep -rn`, `find . -name`, with the path **double-quoted**:
`cd "D:/Taadaa/tiktok-luot nuoi acc" && grep -rn "FEED_SESSION_MIN_TOTAL_VIDEOS" python_runner/tests/...`

## Constants are test-asserted symbolically — no test edit needed
`test_multi_machine_feed_session.py` imports `FEED_SESSION_MIN_TOTAL_VIDEOS` /
`FEED_SESSION_MAX_TOTAL_VIDEOS` and asserts against the symbols
(e.g. `assertEqual(seen_min, {FEED_SESSION_MIN_TOTAL_VIDEOS})`,
`total_swipes_requested == 2 * FEED_SESSION_MAX_TOTAL_VIDEOS`). Changing the
constant auto-updates those tests. Do NOT hardcode 15/30 in tests.
Only numeric literal tied to a different constant: line 778
`assertLessEqual(max(_max_swipes), 15)` refers to `FEED_SESSION_MAX_SWIPES`
(15, unchanged) — out of scope.

## Proving "no new failures" when pre-existing failures exist
Full suite showed 50 passed / 3 failed. To prove the change introduced zero new
failures, isolate the failures against the ORIGINAL code:
`git stash` → re-run only the failing tests → confirm identical failure →
`git stash pop`. The 3 pre-existing failures were
`test_incomplete_lock_alias_identity_is_deferred`,
`test_normal_schedule_rechecks_handoff_before_child_submission`,
`test_normal_schedule_skips_prior_handoff_when_lock_files_are_missing`
(`MagicMock` result-type / `skipped-device-locked` device-lock logic —
unrelated to video constants, out of scope for a simple constant bump).
