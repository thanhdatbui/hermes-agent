# ADB timeout recovery — honest RED/GREEN in a worktree (2026-08-23)

Task contract: bounded `subprocess.TimeoutExpired` retries + opt-in single soft
reboot per recovery window in `AdbClient` (`src/automation_core/adb.py`), tests
in `tests/test_adb_subprocess.py`. No live device commands. Worktree
`automation-core-adb-timeout-wt`, branch `codex/adb-timeout-recovery`.

## Design that landed

- `__init__` gained appended kwargs `reboot_recovery_wait_timeout=120.0`,
  `reboot_recovery_poll_interval=2.0` after the existing
  `allow_device_reboot_recovery=False` flag (which was previously stored but
  never used). API-compatible; consumer config unchanged.
- `run()`/`run_bytes()` bodies collapsed into one `_execute(..., text: bool)`
  executor returning the raw `CompletedProcess`; both wrappers keep their exact
  result types and error-message formats (`"adb command timed out: ..."`,
  `"adb executable not found: ..."`) — the consumer classifies by
  `isinstance(error, ADBError)` + substring (`capture_recovery._blocked_code`).
- Timeout semantics inside `_execute`: non-final attempt timeout → wait-for-device +
  delay → bounded retry; final attempt timeout → if opt-in AND serial present →
  one soft reboot (`adb -s <serial> reboot`, tolerate its own timeout while the
  device tears down) → `wait-for-device` → poll `getprop sys.boot_completed == "1"`
  until bounded deadline → retry original command exactly once; post-reboot timeout
  raises fail-closed. Reboot gate requires `include_serial=True` too — a global
  command (`devices`) must never reboot a device.
- App-level failures (non-zero exit) are RETURNED, never retried or rebooted;
  stderr-marker retry behavior preserved byte-for-byte.

## Honest RED against HEAD without stash — HEAD-src overlay recipe

Problem: `PYTHONPATH=src` always exercises worktree code, so new tests can't show
RED against current production; `git stash` is banned in worktrees (repo-global pop hazard).

1. Extract HEAD's src tree to OS temp WITHOUT touching working files:
   `git archive HEAD src` via subprocess → pipe stdout into
   `tar -x -f - -C <tmp>`. **Windows tar needs explicit `-f -` for stdin** — bare
   `tar -x` tries `\\.\tape0`. `git archive` keeps the `src/` prefix → import root is `<tmp>/src`.
2. Provenance probe FIRST:
   `env PYTHONPATH='C:\...\Temp\adb-red-xxx\src' python -c "import automation_core.adb as m; print(m.__file__)"`
   must print the overlay path.
3. Run focused tests with that PYTHONPATH → record honest RED counts
   (observed: 6 failed / 5 passed with `ADBError: adb command timed out`).
4. Delete the overlay dir; GREEN pass from the worktree with `PYTHONPATH=src`
   and provenance probe again (editable MetaPathFinder on THIS host resolves
   plain imports to the coordinator checkout — always Windows-style PYTHONPATH).

## Bugs the consumer regression caught (core-only suite was green)

1. **Bytes stderr classification**: passing RAW BYTES stderr (`text=False` path)
   into a str classifier raised `TypeError: a bytes-like object is required,
   not 'str'` at the `CONNECTION_LOST_MARKERS` line. Old code classified the
   ALREADY-DECODED string. Fix at the seam:
   decode `errors="replace"` before marker matching. Rule: when consolidating
   two paths into one executor, preserve each path's POST-CONVERSION types at
   every seam, not just at result construction.
2. **Legacy test stubs missing real attributes**: refactor reading MORE off
   `CompletedProcess` (`.args`) broke the old `Completed` stub. Fix the stub
   faithfully (add the real attribute), never weaken production.
3. **Scripted fakes vs real control flow**: with default
   `connection_retry_attempts=3`, reboot-window scripts mis-sequence (filler
   entries consumed as boot probes). Set explicit `connection_retry_attempts=2`
   for reboot scenarios; match recorded calls by argv SUFFIX (adb_path/-s/serial
   prefix the argv), never full equality with logical args.

## Consumer regression command (offline)

```
cd '/d/Taadaa/tiktok-luot nuoi acc'
env PYTHONPATH='D:/Taadaa/automation-core-adb-timeout-wt/src' \
  python -m pytest python_runner/tests/test_adb.py python_runner/tests/test_no_adb_cache_commands.py -q -p no:cacheprovider
```
Provenance probe first (`automation_core.adb.__file__` → worktree src). Run it
whenever the core ADB seam changes; core-only green is NOT sufficient.

## Results (real output, offline only)

- RED (HEAD overlay): 6 failed / 5 passed.
- GREEN core focused: test_adb_subprocess 11 passed; group with test_core +
  no_cache_shell_commands + no_direct_ui_dump: 26 passed.
- Full core suite: 615 passed (one unrelated timing-flaky lease-concurrency test
  passed 3/3 isolated + in rerun; classified pre-existing flake, not caused).
- Consumer: python_runner test_adb + no_adb_cache_commands: 9 passed.
- Static: py_compile OK both files; `git diff --check` clean; CRLF preserved
  (`file` reports CRLF); final status = exactly the 2 allowlisted files.

## Rollout caveat

Consumer executes a versioned wheel/pin — effect on farm requires version bump +
wheel build + pin update between runs (release completeness gate). Source-only
completion is partial delivery; left uncommitted per task non-goals.
