# Schema-Remediation Re-audit Recipe

Use this when a commit claims to close tampering in a generated manifest, signed payload, or cross-linked schema.

## Evidence boundary

- Derive scope from `git diff-tree --no-commit-id --name-status -r <commit>`.
- Read the committed blobs with `git show <commit>:<path>`; separately inspect current callers/tests and pre-existing untracked files.
- Record `git diff --shortstat`, `git diff --numstat <parent> <commit>`, `git diff --check`, compile output, and final status.

## Disposable probe matrix

Start from a real generated/picker payload, not hand-built JSON:

| Probe | Mutation | Required result |
|---|---|---|
| baseline | no mutation | accepted with real source |
| identity | recompute expected IDs using the actual manifest identity | IDs match and baseline remains accepted |
| ordered list | reverse an ordered ID list | rejected after shape/hash gates pass |
| metadata | mutate one top-level field at a time | rejected by the intended source/internal binding branch |
| dependent-hash tamper | recompute block ID, entry IDs, and idempotency keys after mutation | still rejected; otherwise source binding is bypassed |
| source-less | repeat internal-integrity mutations with `source=None` | source authorization may be unavailable, but internal canonical checks must not silently vanish |

For each rejection, capture the exact `ValueError` reason or instrument the branch. `pytest.raises(ValueError)` alone is not sufficient evidence.

## Gate-masking checks

A test is gate-masked when its mutation also violates an earlier invariant, for example:

- changing a block day but leaving payload day or session slots unchanged;
- changing an entry's metadata without recomputing its formula-bound ID;
- reversing IDs while also making the block topology invalid;
- mutating several fields at once so the first failure is unknown.

Reshape the probe so unrelated shape, topology, timestamps, and dependent hashes remain valid. Test each field independently. Bundled tamper tests are useful as defense-in-depth but cannot prove every binding branch.

## Source-less semantics

Do not conflate two contracts:

1. **Authorization:** whether a block/account/machine exists in the supplied `SourceConfig`.
2. **Internal integrity:** whether payload fields agree with their canonical formulas and cross-links.

A source-less validator can intentionally skip authorization, but it should still enforce internal formulas unless the API explicitly documents otherwise. Search for conditional checks such as `if source is not None` around derived identities; then probe the equivalent mutation with and without a source. Preserve any existing test that intentionally demonstrates source-less acceptance of a self-consistent but unauthorized fixture, and explain the distinction in the audit.

## Report structure

Report, in order:

1. verdict and whether the named gate can proceed;
2. exact commit scope and provenance;
3. baseline/canonical/reordered/tampered probe results;
4. gate-masking or source-less bypass findings with `file:line` locators;
5. focused/full test counts, compile, diff-check, and untouched-worktree status.
