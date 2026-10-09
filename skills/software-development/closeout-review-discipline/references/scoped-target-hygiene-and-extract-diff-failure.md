# Scoped Target Hygiene & Working-Tree Diff Integrity in Closeout Gate

## Root Cause
When running `closeout_gate.py --repo <repo> --files <f1> <f2> ...`, Step 2 (`EXTRACT CANDIDATE DIFF`) validates that every targeted file in `--files` actually contains working-tree changes (or staged changes depending on base).
If a safety remediation or cleanup reverts a file back to its baseline HEAD state (e.g. removing an accidental edit from `toolsets.py`), `git status` shows no modifications for that file.
The gate will fail immediately before tests or review with:
```text
✘ Failed to extract diff: targets without working-tree changes: ['toolsets.py']
Exit code: 1
```

## Protocol
1. **Always verify `git status --short -- <targets>` before invoking `closeout_gate.py`**:
   Ensure every path passed to `--files` actually has a non-empty working-tree diff or staged diff.
2. **Exclude clean targets**:
   If a file's edits were undone or discarded during remediation, remove that file from the `--files` parameter list immediately.
3. **Do not confuse clean target failure with code rejection**:
   This is an orchestration parameter mismatch, not a code defect. Do not dispatch worker code repairs for clean-target extract failures.

## Honest Latency & Long-Running Process Communication
- When operations take multiple minutes or exceed foreground thresholds, never dismiss user complaints with claims like "không có treo".
- Check actual timestamps and process runtimes (`time.monotonic()`, process elapsed time).
- Acknowledge long model generation and reviewer latency directly, state the exact active background PID/process ID, and report timeout boundaries honestly.
