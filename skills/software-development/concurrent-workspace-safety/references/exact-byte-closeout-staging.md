# Exact-byte closeout staging in shared worktrees

Use this reference when the user wants an index-only closeout across multiple Git repositories, while forbidding commits, rebases, pushes, source edits, and cleanup of unrelated dirt.

## Required sequence

1. Build an explicit repository/path allowlist. Keep non-Git roots out of all Git mutations.
2. Before the first index mutation, snapshot every repository's `HEAD`, complete `git status --short --untracked-files=all`, complete `git diff --cached --name-status`, and hashes/sizes of all allowlisted worktree files. The complete cached path set matters: a foreign staged path may be hidden by a narrow diff.
3. Validate policy artifacts byte-for-byte from the external baseline/verification artifact. Require:
   - baseline backup hash and size match the artifact;
   - current worktree hash and size match the artifact;
   - current bytes begin with the baseline bytes;
   - the appended suffix contains exactly one `HERMES-DIRTY-SCOPE-RULE-20260831:START` and one `...:END` marker;
   - the current file contains exactly one complete marker block.
4. Construct each policy index candidate as `git show HEAD:<path>` bytes plus only `current_bytes[len(baseline_bytes):]`. Hash it with `git hash-object --stdin`, then install it with `git update-index --cacheinfo <mode>,<blob>,<path>`. This avoids staging pre-existing worktree differences and does not rewrite the worktree.
5. Capture code candidates from fresh working-tree bytes only for the exact code allowlist. Install those exact blobs with the same index-only technique. Never use broad `git add`, `git add .`, `git add -A`, reset, restore, checkout, stash, or clean.
6. After each repository mutation, immediately re-check `HEAD`, complete cached path set, staged blobs, and allowlisted worktree hashes. A single repository-wide script that stages many repos and verifies only at the end is unsafe: a sibling can commit or change the index between repositories.
7. If `HEAD`, the index path set, or a captured worktree hash changes unexpectedly, stop with `CANDIDATE_INVALIDATED_BY_CONCURRENT_WRITER`. Do not replay the candidate on the new `HEAD` and do not normalize or repair the index. Report the last valid hashes separately from the final invalidated state.
8. Final verification must be bound to the final state: re-check `HEAD`/reflog, staged `--name-status`, staged blobs, marker counts, and worktree hashes. A passing check against a superseded candidate is not final evidence.

## Windows and CRLF

Exact CRLF policy artifacts can trigger standard `git diff --cached --check` warnings because Git treats carriage returns as trailing whitespace. Run the standard check and also `git -c core.whitespace=cr-at-eol diff --cached --check`. Report the standard warning honestly; do not alter immutable artifacts to make the check green. Keep code checks separate so policy-artifact warnings cannot obscure code hygiene.

## Concurrent-commit signature

A sibling commit may advance `HEAD` and absorb policy changes during the operation. Confirm with `git reflog`, `git log`, and `git show --name-status <new-head>`. If the target is clean versus the new `HEAD`, it may already have been absorbed; if a target has new unstaged bytes, that is a fresh concurrent change. Neither case authorizes silently reconstructing the old candidate.

## Evidence/reporting

Report per repository:

- pre-action `HEAD`, status, and cached path set;
- final `HEAD`, status, and cached path set;
- exact staged `--name-status`;
- standard and CRLF-aware diff-check result;
- index tree hash and each candidate blob hash/size/SHA-256;
- root/non-Git policy files explicitly excluded from staging;
- whether unrelated dirt was preserved, and whether the candidate was invalidated by concurrency.

Observed failure pattern: a multi-repository index-only staging pass initially produced correct `HEAD + suffix` blobs, but a sibling commit moved one repository's `HEAD` during verification and another repository's index changed. The correct outcome was invalidation and preservation—not restaging from newer bytes or claiming the earlier candidate as final.
