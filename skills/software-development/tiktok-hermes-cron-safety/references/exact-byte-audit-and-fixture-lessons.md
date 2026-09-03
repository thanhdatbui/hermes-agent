# Exact-byte audit and fixture lessons

Use this reference when coordinating a live-safe entrypoint change after an implementation worker finishes. It records durable lessons from a Phase 9A.5 safety review; it is not a statement of current branch status.

## Coordinator/worker ownership

- The implementation worker may write only the approved source/test allowlist and must leave the tree uncommitted.
- The coordinator must wait until every writer has stopped before testing, hashing, auditing, or editing. A missing result artifact is **not** proof that the worker finished.
- Never let the coordinator patch a shared test file while a worker may still be writing it. That invalidates both the worker handoff and any later exact-byte audit.
- Worker self-report, exit code, or a focused green slice is not approval. Independently inspect the exact target worktree, status, diff, tests, and final bytes.

## Exact-byte audit gate

1. Assert the expected branch, baseline `HEAD`, and exact changed-path allowlist.
2. Include **untracked new files explicitly** in the audit bundle. `git diff` alone omits them.
3. Bind every reviewed file with SHA-256, byte count, LF/CRLF count, BOM state, and its full bytes (or an unambiguous exact-byte encoding).
4. Include the baseline-to-candidate diff, relevant plan contract, test output, and static-gate output.
5. Ask the designated auditor for a machine-readable verdict. Treat every finding as blocking unless the governing rules explicitly permit otherwise.
6. After any remediation, discard the old bundle, rerun verification, recompute hashes, and request a fresh exact-byte audit. Approval of old bytes never transfers to edited bytes.
7. Commit only after the final response says `APPROVED` for hashes matching the worktree. Stage with an exact allowlist, verify the staged diff, then commit without amend/push unless requested.

## Canonical manifest fixture trap

`hermes_cron.manifest.load_snapshot()` validates more than JSON schema and SHA:

- bytes must equal `canonical_manifest_bytes(payload)`; and
- the filename must be exactly `<assignment_id>.json`.

A fixture that writes valid canonical bytes to `manifest.json` fails with `MANIFEST_IDENTITY_MISMATCH`. Build the payload first, then write it to:

```python
manifest = tmp_path / f"{payload['assignment_id']}.json"
manifest.write_bytes(canonical_manifest_bytes(payload))
```

Do not weaken production validation to accommodate a bad fixture.

## Fixture isolation trap

Do not reuse the same `tmp_path` for a negative setup that creates `wb/` and a later canonical fixture that also creates `wb/` with plain `mkdir()`. Either:

- allocate a fresh child directory per case (`case_dir = tmp_path / "canonical"`), or
- make fixture directory creation deliberately idempotent only when cross-case contamination is impossible.

Fresh per-case directories are preferred for security tests because stale consume markers, evidence, or lock aliases can otherwise change the tested path.

## Test-gate discipline

- A `-k` expression is only a diagnostic slice. It can silently omit required plan nodes.
- Run required named node IDs explicitly, then the full Phase suite.
- A focused adversarial slice passing does not offset failures in older happy-path tests. Repair the fixture and rerun the entire gate.
- When a stricter validator breaks only fixture construction, prove that diagnosis by calling the validator directly and inspecting its coarse reason before changing source.

## Historical review signal

The initial safety audit found five reusable classes of gap:

1. a truthy/self-asserted verifier instead of evidence-bound `ACCEPTED`;
2. non-atomic permit replay protection;
3. permit-supplied lock availability instead of canonical shared-lock inspection;
4. permit-supplied host/range authority instead of canonical host config; and
5. a fabricated one-entry manifest instead of selecting one unique entry from canonical assignment bytes.

Later adversarial tests for the remediated seams passed, while a broader slice exposed fixture-only failures caused by the two traps above. The durable lesson is to fix test construction, rerun the full gate, and obtain a fresh exact-byte approval—not to relax production checks or commit a partially green candidate.
