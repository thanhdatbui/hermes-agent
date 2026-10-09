# Nested parent-lock handoff: verification recipe

## Trigger
A parent runner owns a device lock and launches a child workflow on the same serial. The child fails before UI work with `ACQUIRE_LOCKS` / `NEEDS_USER_DECISION`, while the lock owner belongs to the parent project. This is a process-boundary ownership collision, not a UI failure.

## Safe contract
- Pass an explicit internal handoff flag from parent argv to child argv (for example `--allow-parent-lock`).
- Persist it through CLI parsing, config storage, and the child `context.config`; a flag missing at any boundary is dead code.
- In the child lock state, use a no-op/unlocked lease only for this explicit handoff. Never set generic `user_authorized`, enable takeover, delete the parent lock, or mutate its status.
- Keep unrelated failures separate: ADB startup timeout, ledger/reservation errors, memory errors, and intentional schedule skips need their own diagnosis.

## Focused evidence
1. Inspect the child artifact and confirm failure state/reason at `ACQUIRE_LOCKS`.
2. Record parent project, child project, serial, lock path, and owner PID/project.
3. Assert the child launcher argv contains the handoff flag.
4. Unit-test the parent-lock branch with mocked lock/device seams and assert no lock-file mutation.
5. Run `py_compile`, the focused boundary test, and a diff/allowlist audit before any farm rerun.

## Anti-patterns
- Re-running every failed machine before classifying lock vs. device vs. ledger failures.
- Treating a worker's summary as proof that the intended worktree changed; re-read the exact files and rerun tests in the coordinator worktree.
- Broadening a parent-lock bypass into a generic lock takeover or manual decision override.
