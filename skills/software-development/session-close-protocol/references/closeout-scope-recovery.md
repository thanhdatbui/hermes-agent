# Closeout scope recovery

Use this reference when a closeout session has accumulated stale candidates, worker handoffs, or concurrent commits.

## Recovery sequence

1. Reconstruct the original deliverable from the user's first request and the confirmed change ledger. Do not infer it from the newest dirty file, TODO, worker summary, or review finding.
2. Write a short allowlist: exact production files, direct tests, review route, and allowed Git operations. Explicitly exclude historical candidates and adjacent subsystems.
3. Freeze `HEAD`, upstream, `git status --porcelain=v2`, `git diff`, and `git diff --cached` before any edit or stage operation. Preserve unrelated dirty files and pre-existing staged paths.
4. If the original deliverable is already committed and remote-verified, stop. Do not reopen it because an adjacent candidate is dirty or a new audit found a concern.
5. If the user explicitly requests “fix until review passes,” reopen only the original candidate. Use one writer in an isolated worktree or a single coordinator-owned writer; never dispatch multiple writers against a shared worktree.
6. After every worker handoff, re-read complete scoped files, re-check HEAD/index/status, run focused verification, and rebuild the exact staged bytes. Any scoped concurrent write or commit invalidates prior evidence and requires reconciliation.
7. Send the exact allowlist to the named `plan-review` model through 9Router. Never substitute the session model or implementation worker. Bind the verdict to the staged tree/hash.
8. Commit/rebase/push only after the final exact candidate is approved and verified. If scope or provenance cannot be separated, stop with `BLOCKED_AT_SCOPE_RECONCILIATION` rather than cleaning, resetting, or guessing.

## Failure patterns to avoid

- A valid rejection on one candidate does not authorize importing a different historical candidate.
- Passing tests or a worker “done” message is not model approval.
- A progress/closeout request is not permission to expand into TOCTOU, lock, recovery, or unrelated hardening.
- `git add -A`, `reset --hard`, `clean`, and broad whole-file staging are not conflict resolution.
- Repeated polling is not progress when no valid review request is in flight.

## Reporting

Use the concise structure `Mục đích → Kết quả → Blocker → Remote`. Name the exact review route, candidate scope, and gate result; separate “implemented by worker” from “verified by coordinator.”