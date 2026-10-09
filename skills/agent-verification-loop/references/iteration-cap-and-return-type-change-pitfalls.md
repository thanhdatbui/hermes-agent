# Pitfall: Iteration Cap Reached Before Pytest Goes Green

## What happened (2026-09-08)

A session applied patches to `alerts.py`, `batch_aggregator.py`, and `test_alerts.py` in sequential
turns. Each patch fixed one thing but created or exposed the next failure. The turn cap was hit before
`python -m pytest` ran green. The gate was never satisfied.

## Root cause

1. First pytest run revealed 8 pre-existing tests broken by a `bool → dict | bool` return-type change.
2. The fix (adding `monkeypatch.setenv("AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT", "1")` to each of
   the 8 tests) was prepared — but the iteration limit hit before the final consolidated pytest run.

## Rules to avoid this

### Rule 1 — Batch all call-site fixes for a return-type change into ONE patch
When a function changes its return type (e.g. `bool → dict | bool`), collect every affected test in
a single `patch` call. Do NOT fix them one per turn and re-run pytest after each to see which
failed. A single `patch(mode='patch')` with all 8 hunks at once, followed by one `pytest` run,
keeps the turn budget in range.

### Rule 2 — Run pytest ONCE after all code+test patches are done, not after each individual patch
Pattern that works:
```
Turn N:   patch production code (alerts.py suppression logic)
Turn N:   patch batch_aggregator.py (load_results_from_run_dir)
Turn N:   patch test_alerts.py (all 8 broken tests + 3 new suppression tests in ONE call)
Turn N:   patch test_batch_aggregator.py (new TestLoadResultsFromRunDir class)
Turn N:   run `python -m pytest tests/test_alerts.py tests/test_batch_aggregator.py -p no:cacheprovider -v`
```
All of this fits in 4–5 tool calls if batched aggressively (independent patches in parallel).

### Rule 3 — Anticipate which pre-existing tests break BEFORE patching production
Before making the production code change, scan test files for assertions on the return value
(`is True`, `is False`, `assert res`) of the function being modified. If the return type changes,
those assertions break. Prepare the fix in the same batch.

## Iteration budget heuristic

A multi-file patch task involving:
- 1 production module (alerts.py) — ~2 patch calls
- 1 utility module (batch_aggregator.py) — ~2 patch calls
- 2 test files — ~2 patch calls
- 1 final pytest run — 1 terminal call

Total: ~7–8 tool calls minimum. If starting with skill loading (2 calls) + file reads (4 calls),
the budget is often already at ~6 before the first patch. Pre-read only the files you will
definitely patch; skip reads on files you only need for context if the content is already visible
in an earlier turn result.

### Rule 4 — Cross-Platform Path Handling with rg/pytest under MSYS/Git-Bash
On Windows hosts where the agent shell runs via MSYS/Git-Bash:
1. `search_files` backed by `ripgrep` (rg) can fail with `os error 3 (The system cannot find the path specified)` when given POSIX-style paths like `/d/Taadaa/...`. Always pass Windows native paths (`D:/...` or `D:\...`) or search relative to the current working directory.
2. `pytest /d/Taadaa/...` fails with `file or directory not found` because pytest uses native Windows Python path resolution. Always pass Windows drive paths (`pytest D:/Taadaa/...` or `pytest D:\Taadaa\...`).
3. Batch independent exploration calls (e.g. baseline pytest run + grep/read of patch anchors) in parallel in turn 1 to preserve iteration budget for execution and verification.

### Rule 5 — Tight Tool Budget Execution Discipline (Tasks with Budget <= 4–5 Calls)
When a task specifies a strict call budget (e.g. `Budget <= 4 calls`) or involves adding targeted tests:
1. **Zero Exploratory Drift**: Do not trace secondary subsystems, read large service files (e.g. `accountSemaphore.ts`, `combo.ts`), or paginate multiple sections of unrelated code. The task is to append test cases to an already identified test file.
2. **Minimum Viable Turn Sequence**:
   - Call 1: Read the target test file to understand imports, conventions, and existing cases.
   - Call 2: Apply the test cases using `patch` directly to the target test file.
   - Call 3: Run the focused test runner (`npx vitest run <file>` or `node --test <file>`).
   - Call 4: Report real execution output.
3. **Exploration Traps**: Avoid exploratory `search_files` or `terminal("grep ...")` when the target file and function name are already specified in the prompt. Every extra exploratory call reduces the remaining turns and risks hitting the iteration limit before code modifications and test verification can complete.
