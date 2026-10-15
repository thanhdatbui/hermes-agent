# Haiku Worker Monolith-Editing Rules & Turn Clamping Patterns (2026-10-15)

## 1. Context & Background
During the modularization of `feed_session_watchdog.py` (2.088 lines) down to 1.373 lines, several key execution patterns and pitfalls were observed when driving `haiku_worker.py` against large monolith scripts.

## 2. Key Pitfalls & Workarounds

### Pitfall 1: Max-Turns Exhaustion on Disparate Edits
- **Symptom:** Haiku worker exits with `Error: Reached max turns (6)` without completing the patch.
- **Root Cause:** When prompted to edit imports at line 35 AND simultaneously delete 4 functions spanning lines 480 to 1150 in an 1800-line file, Haiku performs multiple `read_file` inspection turns to verify each location, depleting its 6-turn budget before executing edits.
- **Remediation:**
  1. Slice edits into atomic single-hunk operations (e.g. Turn A: add import + remove function 1; Turn B: remove function 2).
  2. For files > 1.500 lines requiring 2+ distinct hunk changes, set `--max-turns 12` explicitly.

### Pitfall 2: Host Terminal Foreground Timeout (60s)
- **Symptom:** Terminal command aborted with `GUARD_FOREGROUND_TIMEOUT_EXCEEDED: timeout=90s > 60s`.
- **Root Cause:** Coordinator guard on Windows host restricts all foreground commands to `<= 60s`. Multi-turn worker runs on large files with `--max-turns 12` typically require 40–80 seconds.
- **Remediation:** For any worker command needing `timeout > 55s`, invoke via `terminal(background=True, notify_on_complete=True, timeout=120)`. The background harness polls cleanly and awakens the Coordinator upon process exit.

### Pitfall 3: Subagent Test Generation Signature Drift
- **Symptom:** Generated test suite fails with `TypeError: func() got unexpected keyword argument` or `missing required positional argument`.
- **Root Cause:** If the worker prompt only says "Create tests for merge_machine_result", the subagent guesses a single-dict signature `merge_machine_result(result)` instead of the actual `merge_machine_result(prev: dict, new: dict)` signature.
- **Remediation:** In the dispatch contract, explicitly list exact parameter names, types, and expected input/output shapes for each test case.
