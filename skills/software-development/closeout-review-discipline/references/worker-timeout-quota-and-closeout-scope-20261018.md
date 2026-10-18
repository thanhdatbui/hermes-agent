# Worker Timeout, Quota, and Closeout Scope Incident

## Reusable failure pattern

A worker wrapper used a 60-second timeout for an agentic coding path that could spend multiple turns reading, editing, and running focused tests. Raising the timeout alone is not sufficient evidence: the effective timeout must be asserted, the timeout branch must be tested, and the wrapper's output must be inspected. In this incident, `sol_repair.py` exited 0 while reporting no findings; that was a generated artifact, not a valid repair.

## Required evidence sequence

1. Read the actual role configuration and all call-site defaults; do not infer from a prior report.
2. Check the selected model alias against the live CLI/router. An alias can be syntactically configured yet rejected at runtime as `unrecognized_model`.
3. Check quota before dispatch. A quota guard may block the worker even when the process wrapper starts successfully.
4. Run focused tests for: worker success, worker timeout with fallback, `--no-fallback`, deprecated/missing model marker, planner/reviewer timeout, executable-not-found, and fallback failure.
5. Inspect repair JSON for `valid`, findings, patch count, error/model fields, and timestamp. Exit code 0 only means the wrapper completed.
6. Before closeout, establish an exact owned allowlist and implementation/test pairing. A shared repository's unscoped `HEAD~1` diff can exceed the 30KB gate ceiling because of unrelated dirty work.
7. Report three states separately: code/test verification, reviewer approval, and push/remote verification. Never collapse green tests into DONE.

## Evidence labels

- `TEST_GREEN`: focused tests pass on current bytes.
- `ARTIFACT_VALID`: repair/review artifact has valid structured output and actionable findings or approval.
- `REVIEW_APPROVED`: closeout gate returns the required approved verdict for the exact scope.
- `DISPATCH_BLOCKED`: quota, model alias, credentials, or backend availability prevented the requested worker from running.
- `SCOPE_UNCHECKED`: no reliable session-owned allowlist exists for the shared worktree.

These labels are independent; one must not be substituted for another.
