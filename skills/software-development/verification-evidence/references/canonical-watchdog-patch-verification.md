# Canonical watchdog patch verification recipe

Use for a narrowly scoped `merge_follow_result` or equivalent feed-session watchdog patch when the harness reports `verification status: unverified`.

## Patch contract

- Inspect the exact canonical files and unique anchor before editing.
- Patch only the named source files; preserve unrelated dirty files and policy documents.
- If a mirrored Hermes copy is named, apply and verify the same behavior independently.
- `FOLLOW_FAILED` is failure evidence, not committed follow evidence: publish `followed=[]`, `followed_count=0`, `mode1_followed_count=0`, and `mode2_followed_count=0`.
- `OK`/successful results must retain the actual follow list and merged counts.

## Fresh ad-hoc probe

1. Snapshot existing `%TEMP%/hermes-verify-*.py` names.
2. Create a self-contained probe with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), delete=False)`.
3. The probe should import each changed file by absolute path and assert:
   - `FOLLOW_FAILED` in `new` clears all committed follow fields.
   - `FOLLOW_FAILED` in `prev` also clears all committed follow fields.
   - `OK` + followed users preserves the merged list and counts.
4. Execute the exact generated path in a top-level command, not only through an opaque launcher. If the harness static scanner expects a test runner invocation, running `pytest -q "<temp_probe_path>"` executes and registers the ad-hoc probe reliably.
5. Remove only the probe owned by this run and verify it is absent; preserve pre-existing verifier files.
6. Report it explicitly as **ad-hoc verification**, with literal command, real output, exit code, and cleanup result. Do not call it full-suite green.
