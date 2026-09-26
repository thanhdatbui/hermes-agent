# A-to-Z execution, Sol gate, and closeout lessons

## Trigger

Use when the user says “làm từ A–Z”, “làm đi”, “sửa cho xong”, “chốt phiên”, or equivalent.

## Required behavior

1. Treat A-to-Z as an execution contract, not a progress-update request. Continue until `DONE` or `BLOCKED` with concrete evidence; `IN PROGRESS` is never terminal while worker, test, review, canary, or closeout remains.
2. For code/workflow changes, run the Sol planning gate before dispatching an implementation worker. Verify the Sol plan against the effective target path, unique anchor, allowlist, test command, and repository identity. A stale path in a plan must be resolved read-only; never silently switch repositories or subsystems.
3. On “chốt phiên”, run the canonical closeout gate. Any non-zero exit, timeout, rejected verdict, or score below threshold becomes an active remediation task. Repair only the narrowest evidence-backed blocker, rerun the exact failing test, then rerun closeout. Do not claim close, push, or commit from an earlier partial pass.
4. Bind delegated evidence to the exact target repository. A worker that inspected another repo is irrelevant and must be discarded.
5. A focused timeout may hide a deterministic first failure. Reproduce in the exact repo with bounded verbose output; identify the first failing node before editing. Fix only the proven fixture/contract and preserve unrelated dirty files.
6. If a test expectation conflicts with a live default constant, inspect production defaults and neighboring tests before changing either side. A stale assertion is a test-contract defect, not automatic evidence of a production regression.

## Evidence checklist

- exact repo and branch
- exact command, exit code, and timeout behavior
- first failing test and traceback
- allowlisted patch paths and diff/numstat
- focused rerun result
- final closeout verdict and score
