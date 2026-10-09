# Partial Diff After Worker Timeout

## Trigger

Use when a code worker times out after making tool calls and the shared repository may contain an uncommitted partial patch.

## Evidence-first sequence

1. Treat the timeout as transient; do not count it as structural failure yet.
2. Inspect only the task allowlist:
   - `git status --short -- <allowlist>`
   - `git diff --stat -- <allowlist>`
   - `git diff --numstat -- <allowlist>`
   - `git diff -- <allowlist>`
3. Preserve unrelated dirty files and never use reset/revert-all/clean.
4. Classify the result:
   - **No diff:** retry with a narrower contract; if a Fix Code task has `files_modified == 0`, it is structural failure.
   - **Partial but bounded diff:** stop overlapping implementers and dispatch a read-only verifier.
   - **Unsafe/out-of-scope diff:** report evidence and follow the escalation rules; do not silently repair it.
5. Verification must be offline and focused:
   - mocked `pytest` for logic changes;
   - `py_compile` only for syntax-only changes;
   - never use ADB or a live canary as a substitute for the focused test.
6. A worker summary cannot establish correctness. Require actual diff and command output.
7. Keep incident proof separate from code proof. Missing/stale machine artifacts mean the live root cause remains `UNPROVEN` even if the offline patch passes.

## Reporting template

```text
WORKER_STATUS: TIMEOUT / COMPLETED
PARTIAL_DIFF: <paths>
NUMSTAT: <added> <deleted> <path>
SCOPE_CHECK: <in-scope/out-of-scope>
FOCUSED_CHECK: <literal command>
TEST_RESULT: <literal output/status>
LIVE_INCIDENT: CONFIRMED / UNPROVEN
NEXT_GATE: verifier / exact surgery / canary / blocked
```
