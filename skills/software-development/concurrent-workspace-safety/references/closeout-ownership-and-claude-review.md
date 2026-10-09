# Closeout ownership and reviewer loop

## Incident pattern

A worker can implement a state machine and tests in a shared checkout, then a later worker can rewrite the same physical file from an older snapshot. Prompt allowlists do not prevent this. Symptoms include tests referencing symbols absent from production, focused tests failing with `AttributeError`, and a previously green implementation disappearing.

Do not attribute this to sync software without path/provenance evidence. Confirm the collision from current bytes, mtimes, diffs, and worker receipts.

## Required closeout semantics

For `chốt`, `chốt phiên`, `done`, or `xong`:

1. Closeout is an execution loop, not a status report.
2. Run focused verification for the owned candidate.
3. Run the mandatory closeout gate.
4. A rejection or score below threshold means remediation, not termination: read finding → bounded patch → focused verification → reviewer again.
5. Stop only at `APPROVED >=85` or a true non-recoverable `HARD_STOP` with evidence.
6. `BLOCKED`/`REJECTED` are intermediate states unless the hard-stop predicate is proven.

## Ownership design

Use layered protection:

- **Isolated worktree per session/worker:** primary physical isolation; workers return a commit/diff receipt.
- **Per-path lease:** `{session_id, canonical_path, lease_id, base_blob_sha, expires_at}` with atomic acquire, renew, release, and guarded takeover.
- **Pre-write CAS guard:** validate live lease, canonical path, expiry safety margin, and current SHA before atomic temp/fsync/replace. Any error denies the write and reports ownership loss.
- **Coordinator-only merge:** integrate sequentially; same-hunk conflicts remain conflicts; do not use last-writer-wins.
- **OS locks:** only protect short lease-registry critical sections; they do not replace ownership or worktree isolation.

Closeout must evaluate `dirty_files ∩ owned_paths(session)`. Foreign dirty is reported and preserved, not reverted, stashed, or included as an unrelated monolithic test. Without a session manifest/identity, label the result `FOREIGN_SCOPE_UNCHECKED`.

## P1/P2 review checklist

Before moving from P1 lease to P2 guard, reviewer must verify:

- canonical absolute path identity with Windows case normalization and separate display path;
- path containment check (`path.relative_to(repo_root)`) strictly precedes any `path.exists()` probe to prevent filesystem probing outside repository boundary;
- atomic temp/fsync/publish and no partial record;
- per-path lock token/lease-id CAS, guarded takeover, and corrupt-record fail-closed behavior;
- deterministic per-path lookup so an unrelated corrupt record cannot block healthy paths;
- malformed/overflow/deep JSON never becomes an empty healthy registry;
- duration inputs (`max_write_duration`, `clock_skew_margin`) strictly validated: reject booleans, non-finite values (`NaN`, `+/-inf`), and negatives fail-closed with `INVALID_REQUEST`;
- single safe expiry helper catches all exceptions and validates finite clock and expiry: `NaN`/`-inf` clock returns `CLOCK_ERROR` instead of bypassing `< margin`;
- both expiry checks (post-renew and pre-`replace`) route through the safe expiry helper, aborting before replace, unlinking temp files, and releasing/reporting ownership;
- guard renew requires `RENEWED`, and any `registry.get` exception or failed `registry.renew` safely releases lease and returns `release_code` and `ownership_report`;
- current SHA matches base or session's last SHA; base drift denies without mutation;
- post-replace durability errors record the new SHA and report ownership status;
- all clock/read/registry errors fail closed and release/report.

Focused green tests are necessary evidence but not the reviewer verdict. Re-run the reviewer against the exact current source after every remediation round; a reviewer approval binds only to the bytes supplied for that review.

## Recovery rules

- If a worker times out, re-read the exact files and status before retrying; do not assume its self-report or replay a whole-file patch.
- Never use reset/restore/checkout/stash/clean to recover a collision in a shared worktree.
- If a target is overwritten, recover from an explicit artifact/isolated worktree or reconcile manually with current bytes; preserve unknown dirty changes.
- Keep production implementation and its focused tests in one ownership unit. Do not accept a test-only artifact as implementation proof.
