# Threshold/Top-Up Closeout Evidence Checklist

When a closeout reviewer rejects a pipeline candidate that raises a completion threshold (for example, raising `<30` or `<40` to `<45` videos):

## 1. Single Authoritative Policy Value
- Define one shared constant/policy source for the threshold.
- Propagate it across:
  - Detection query (e.g. `video_count < THRESHOLD`)
  - Progress summary / gate logic
  - Command builders / defaults (e.g. `--min-videos`, `--target-videos`)
  - Reservation / top-up decisions (e.g. `current_cnt < target_min`)
  - Validation rules
  - Telemetry payloads
- Run a targeted search across all scoped files to confirm no stale literals remain.

## 2. Backward Compatibility
- Decide explicitly whether legacy CLI values are accepted or rejected.
- Never silently change operator semantics without tests.
- Add regression tests covering:
  - Rejected legacy values (with clear fail-closed error messages)
  - Accepted values at or above the new threshold
  - Default invocations matching the new policy

## 3. Boundary & Branch Matrix
- Test exact boundary values: immediately below (e.g. 39, 40, 41, 44), at (45), and above threshold.
- Test all operational branches:
  - `RESERVE_TOPUP`
  - `RESERVE_DECISION` (skip vs reserve)
  - `complete_partial` status handling
  - `insufficient_pool` handling
  - Operational / DB error paths

## 4. Mocked Orchestration & Downstream Safety
- Add at least one mocked integration test verifying the full pipeline seam:
  `rescan detection -> command construction -> reservation -> top-up action`.
- If an input invariant is relaxed (e.g. `load_niches` accepting `>=80` instead of `==80`), reviewers flag this as unmotivated invariant erosion unless upstream explicitly expanded slots; if retaining `==80`, assert strict validation; if relaxing, test a real downstream consumer to prove deterministic indexing/allocation and absence of unintended side effects.
- Stale git locks: when background processes abort or time out, check and clear stale `.git/index.lock` before staging candidate files to avoid lock collision aborts.
- Suppress pytest plugin autoload failures: if global/venv plugins fail with `ModuleNotFoundError` (e.g. `platformdirs.pytest_plugin`), pass `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` or `-p no:...` flags.

## 5. Test Suite Execution
- Run focused test modules first with clean import context (`PYTHONPATH= pytest -q -p no:cacheprovider`).
- Attempt the repository test suite with third-party plugin autoload disabled under a bounded timeout.
- Distinguish test-runner/environment setup errors (e.g. missing plugin) from genuine test failures.
