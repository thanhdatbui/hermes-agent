# P1 offline harness audit checklist

## Trigger
Use this checklist for scheduler/orchestration/core-harness work with canonical manifests, append-only journals, recovery state machines, lock/CAS claims, or fail-closed dispatch. It is especially important when the user asks for a standing goal such as “tự chạy tự audit cho đến khi xong”.

## Terminal gate
Do not call the task complete because a worker says “done”, `HANDOFF.md` says tests passed, a process exits 0, or one test suite is green. Completion requires all of:

1. Independent reviewer verdict `APPROVED` as the first non-empty line of the final reviewer response.
2. Coordinator-run import/compile, targeted tests, diff/allowlist check, and adversarial invariant probes.
3. No unresolved P0/P1/NEEDS_PROOF item that affects the acceptance contract.
4. No live/device/workbook/credential side effect outside scope.
5. Commit/push only if the task/governance explicitly requires it and staging is verified.

If any gate is missing, preserve the loop state as `IN_PROGRESS` or `FINAL_BLOCKED`, never `DONE`.

## Role and prompt separation
Keep four artifacts separate:

- `plan-audit-prompt/result`: read-only feasibility/spec review.
- `worker-prompt/result`: implementation instructions only; never append the auditor’s role prompt or old audit transcript.
- `implementation-audit-prompt/result`: independent review of the actual worktree.
- `checkpoint`: process IDs, worktree state, artifact paths, current verdict, next action.

A previous failure mode appended a full auditor prompt to a worker brief. The worker then treated audit instructions as implementation input, produced oversized repeated output, and the coordinator could not reliably distinguish self-report from review evidence. Build a short worker brief from the finding list instead.

## Reconcile → patch → re-audit loop
For each `REJECT`/`MINOR_FIXES`:

1. Extract every finding into `ID / locator / trigger / consequence / evidence / required invariant`.
2. Group findings by root cause (canonical validation, atomicity, identity, recovery, sanitizer) rather than adding more prose to the contract.
3. Dispatch one fresh worker with only that grouped brief and the exact allowlist.
4. Have the worker add or update regression tests, then run the project’s write-capable test command.
5. Reconcile the actual worktree and artifacts; ignore worker/HANDOFF self-approval.
6. Run fresh adversarial probes, then a fresh independent reviewer on the actual diff.
7. Repeat until `APPROVED` or a real hard stop. A context/tool limit is not a hard stop; continue from the checkpoint in the next turn.

If two rounds repeat the same structural findings, stop appending contract prose. Replace the design with one canonical source of truth plus executable validators/reference fixtures, then audit that materially different design.

## Adversarial probe matrix
For a fail-closed scheduler harness, directly mutate/replay these cases and assert rejection/no side effect:

### Manifest and time
- slot moved into a reserved block (`12:00`/`17:00`), sub-minute (`06:00:30`), wrong logical day, or interval outside `[D 06:00, D+1 01:00)`;
- `entry_id`/manifest path traversal, non-derived idempotency key, duplicate entry/resource/identity, invalid row `0`/`7`;
- naive, future, UTC-offset, malformed, or non-HCM timestamps;
- assignment/manifest/source revision changed after generation.

### Source mapping and active state
- state revision differs from the payload used to generate the manifest;
- one machine maps to two serials, one serial to two machines, duplicate/missing account IDs, or feed/post row mismatch;
- malformed/torn/mismatched `ACTIVE.json`, more than one candidate manifest, and force-regeneration racing with a launch/recovery reservation.

### Runner and journal
- dry-run must return before lock inspection, adapter preparation, spawn, or any live side effect;
- mutate an entry object after loading and assert it is rejected as not an exact canonical member;
- at `00:00–00:59`, use the prior logical-day manifest; at `01:00–05:59`, assert no blind due entry;
- malformed or identity-mismatched JSONL must fail closed, not be silently skipped;
- crash after `LAUNCH_RESERVED`/`RECOVERY_RESERVED` must reconcile or hand off, never launch/recover blindly; terminal duplicate reports must not call an adapter twice.

### Verifier, recovery, and notifications
- real artifact shape (`multi-machine-feed-session` and `multi_machine_summary`), ambiguous identity, stale tree, wrong final status, and run duration beyond a tiny tolerance;
- cap attempts exactly `2..8` (seven live attempts) under concurrent/duplicate watcher calls;
- sensitive or unrecognized classifications (payment, workbook/data write, authorization/credential, destructive, login/OTP/2FA/CAPTCHA/security, unknown crash, unverifiable lock) must not auto-recover;
- `UNKNOWN` recovery result must hand off without retry transition; `VERIFIED_SUCCESS` requires recapture + retry + identity proof;
- absolute/traversal/workbook/secret-like evidence paths, unbounded strings/lists, empty handoff evidence, duplicate `FINAL_BLOCKED`, and reordered notification target dictionaries.

## Evidence handling
Use an extractor for huge result files: read only the first non-empty verdict line, section headings, locators, and tail after the final response marker. Do not repeatedly page through multi-megabyte patch output. Store prompt/result paths and iteration metadata so a compacted session can resume.

When a read-only reviewer cannot create its own temporary pytest state, label that limitation precisely and rerun the tests in the write-capable worker/coordinator environment. Do not convert a worker’s prior “25 passed” claim into fresh independent proof.

## Windows repository hygiene
For a pre-existing CRLF `HANDOFF.md` or policy file, edit through binary Python read/replace/write, preserve the original EOL style and final newline, then verify byte counts and `git diff --check`. Never let a small append silently rewrite the entire file’s line endings.
