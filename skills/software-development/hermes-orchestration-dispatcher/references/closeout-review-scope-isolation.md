# Closeout review scope isolation

Use this checklist when the user says `chốt phiên`, `chốt`, `đóng phiên`, or asks to continue until reviewer approval.

## 1. Freeze the candidate

- Identify the exact intended files from the current task.
- Preserve unrelated dirty files, generated artifacts, runtime state, and other workers' changes.
- Stage only the intended allowlist and verify:

```bash
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

- If the work is already committed, choose a base that isolates that commit or pass a narrowly constructed diff to the reviewer. Do not use a broad `HEAD~1` when unrelated sync/runtime commits are included.

## 2. Treat reviewer output as actionable state

- `REJECTED` means extract concrete findings and continue; it is not automatically a final blocker.
- Classify each finding as:
  - **code defect** — patch the production path;
  - **missing evidence** — add a focused offline/mock test or deterministic verification;
  - **scope contamination** — narrow the candidate and re-review without touching unrelated files.
- Keep the loop bounded and evidence-driven:

```text
review -> classify -> exact patch -> focused test -> isolated review
```

## 3. Worker timeout handling

- A timeout/no handoff is **TRANSIENT** until disk evidence proves a structural failure.
- Retry at most once with a materially narrower exact contract and a fail-fast abort clause.
- Verify the shared workspace independently after the worker returns: status, diff, target files, compile/test output.
- Never trust a worker's completion prose as proof and never repeat a broad prompt unchanged.

## 4. Evidence for policy/config and lane changes

String-presence assertions are not enough. Add small offline behavioral tests that exercise the relevant branch or hook using mocks/stdin and no network, ADB, device, account, or farm state.

For a CLI lane/flag change, cover:

- default invocation compatibility;
- each explicit lane;
- `all` ordering and both underlying calls;
- state-save/status semantics;
- the branch that previously failed;
- guard conditions such as already-run, active runner, and active device lock when those gates are in scope.

For policy/config changes, validate YAML/JSON parsing, configured hook paths/timeouts, forbidden routes, and actual hook allow/block behavior offline.

## 5. Closeout gate and push

- Run the exact focused test first and retain its real output.
- Run `closeout_gate.py` against the isolated candidate.
- Only `APPROVED` with score `>=85` permits commit/push reporting.
- After commit, require fresh pre-push hook evidence for the same candidate. If remote branches diverge, reconcile deliberately; never force-push merely to make the command pass.
