# Plan authority reconciliation — contaminated remote + quarantine provenance

Class of drift the standard `plan-baseline-drift.md` pre-flight does NOT cover:
the plan's stated baseline is correct for local `HEAD`, but the LIVE repo has
moved around it — `origin/master` advanced with unapproved bytes, a quarantine
ref carries parallel provenance, and a dangling object floats free. The plan must
reconcile authority WITHOUT adopting any NON-EVIDENCE byte.

## When this fires
- `git rev-parse HEAD` still equals the plan's claimed baseline (e.g. `910a8add`),
  but `git rev-parse origin/master` is ahead (e.g. `1146c202a82b7a7dd006e0d0252b78eb2f1218bd`).
- A merge-base exists (`git merge-base HEAD origin/master` == local HEAD) — it is
  NOT a divergent fork, it is a fast-forward the local worktree never took.
- Implementation commits exist in the wild (origin and/or a `quarantine/...` ref)
  that were never approved through the plan gate. Local worktree/source is still
  the prior Phase baseline.

## Containment probe (run BEFORE trusting any plan-stated ref fact)
For every suspect SHA, test ancestry against each ref with the SAME primitive:

```bash
for c in cb086680072bd563b4655535db1c906195617607 \
         c69d159 6696e6b 9d096c9 b772b76; do
  for r in HEAD origin/master quarantine/phase9-out-of-gate-20260813-b772b76; do
    if git merge-base --is-ancestor "$c" "$r"; then echo "$c in $r"; else echo "$c NOT in $r"; fi
  done
done
```

This catches the non-obvious case `plan-baseline-drift.md` misses: a commit can be
an ancestor of BOTH `origin/master` AND the quarantine ref (so it is NOT
"only in quarantine"), while other commits are only in the quarantine ref, and a
fourth is dangling (in NEITHER HEAD, origin, nor quarantine). Never write
"quarantine contains <sha>" for a sha that `merge-base --is-ancestor` proves is
unreferenced. Verified live example (tiktok-luot nuoi acc, 2026-08-13):
`c69d159`/`6696e6b` in BOTH origin and quarantine; `9d096c9`/`b772b76` only in
quarantine; `cb086680...` dangling in neither.

## Provenance preservation (no deletion, GC-safe)
- A dangling object must be pinned before any GC:
  `git update-ref refs/quarantine/phase9-cb08668-non-evidence <sha>` (dedicated ref).
- Verify the EXISTING quarantine ref still resolves and contains the commits you
  claim: `git rev-parse -q --verify <ref>` plus `git merge-base --is-ancestor
  <each> <ref>` for the c69/669/9d/b772 set.
- NEVER delete a quarantine ref. The forensic no-deletion guard is
  `git cat-file -e <sha> && echo REACHABLE`.

## Forbidden mutations during reconciliation
Do NOT use `git reset --hard`, `git checkout --`, `git clean -fdx`, force-push,
blind `pull`/`rebase`, or `git cherry-pick` of implementation commits. Policy-only
commits on contaminated ancestry (`0c6201e`/`1146c20`) must also NOT be
cherry-picked — their ancestry includes the implementation commits; if their diff
is needed, reapply/review it as a fresh explicit-allowlist policy change under its
own gate.

## Isolated clean authority branch (the build surface)
Create, do not rewrite: `git branch phase9-authority-<base> <base-sha>`. The base
must be proven to exclude every NON-EVIDENCE commit:
`git merge-base --is-ancestor <five NON-EVIDENCE SHAs> <authority-branch>` must all
be FALSE, and `git log --oneline -1 <authority-branch>` must equal the baseline.
Local dirty main worktree stays untouched. Build tasks run ONLY on this branch.

## 9R authority-reconciliation gate (inject before the first implementation phase)
A mandatory, plan-only-now gate that runs its Git operations only AFTER the plan
is exact-hash APPROVED by an exclusive worker, and remains NO-LIVE:
1. Re-fetch/re-probe exact refs/status immediately before implementation; any
   further drift re-blocks/replans.
2. Preserve cb08668 provenance (dedicated ref, no deletion); verify existing
   quarantine ref resolves + contains expected commits.
3. No forbidden mutations (list above).
4. Do NOT cherry-pick policy-only contaminated-ancestry commits.
5. No push/merge/release/cutover/master rewrite. `origin/master` is
   contaminated/non-authoritative → any push/merge to it is FINAL_BLOCKED until an
   explicit owner decision; never silently merge contaminated ancestry back.
6. Map it into: ordered task list (9R before 9A.1), rollback table (refs only,
   never delete quarantine), stop conditions, acceptance matrix (e.g. F-00), and an
   AG exact-byte audit gate on the 9R scope before any build.

The remote/default-branch remediation is a LATER explicit owner decision, out of
the plan's implementation scope.
