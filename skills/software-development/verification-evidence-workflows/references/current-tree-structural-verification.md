# Current-tree structural verification

Use this reference when a sibling worker or concurrent session changed a scoped
file after the last read checkpoint and the platform requests fresh evidence.

## Minimal Windows recipe

1. Snapshot `%TEMP%/hermes-verify-*.py`, `git status --short`, working/cached
   scoped paths, and SHA-256 hashes.
2. Re-read the live changed regions. Do not patch, revert, re-stage, or normalize
   an overlapping scope during verification-only work.
3. Generate the verifier with:

```python
NamedTemporaryFile(
    prefix="hermes-verify-",
    suffix=".py",
    dir=tempfile.gettempdir(),
    delete=False,
)
```

Run it from the repository root with `PYTHONPATH` explicitly controlled.
4. In the verifier, parse the live module with `ast`, inspect changed wrapper
   call sites, and compare every keyword argument with the callee signature.
   Resolve every referenced helper name with AST/import inspection or a real
   import. Then run a mocked NO-LIVE seam probe.
5. Delete only the verifier created by this run and prove it is absent. Preserve
   pre-existing verifier files.
6. Run the canonical focused pytest and static checks independently. Report
   verifier status separately from pytest status.

## Failure classification

A verifier failure caused by an internal production mismatch is a real blocker,
not a harness failure. Examples include:

- a wrapper calls an undefined helper such as `shallow_copy`;
- a wrapper passes `hard_deadline=` while the callee signature lacks it;
- an import resolves to a different checkout because `PYTHONPATH` was not
  controlled.

Do not claim `FIX_COMPLETE` from AST success, a passing isolated helper probe, or
an earlier pytest run when the current tree fails this structural gate. Report
`VERIFIED_CURRENT_TREE` only as evidence about the current bytes, and keep the
source ownership conflict explicit.

## Why this matters

Large Python modules often receive coordinated edits in multiple hunks. A worker
can land an executor wrapper before the matching child signature or helper import.
Python parsing and partial unit tests may still pass, while the real execution
path fails immediately. Structural call/definition checks catch that gap before
acceptance is reported.
