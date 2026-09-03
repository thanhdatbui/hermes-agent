# Candidate-byte reconciliation

Use this when a closeout candidate is assembled in a dirty/shared worktree, especially when the same files contain unrelated edits or the index already contains foreign staged paths.

## Rule

A review verdict and test result bind to exact bytes, not filenames, intent, or an unchanged `HEAD`. Any scoped-file drift after review invalidates the verdict and evidence.

## Safe recipe

1. Freeze and record:
   - repository, branch, `HEAD`, upstream SHA;
   - `git status --porcelain=v2 --branch`;
   - unstaged and staged path sets;
   - exact production/test allowlist;
   - per-file hashes, byte counts, line-ending state, and mtimes.
2. Separate the candidate from foreign dirt. Do not stage a whole mixed file. Reconstruct each candidate file in an isolated temporary directory from `git show HEAD:<path>` plus only the approved hunk(s). Keep unrelated same-file changes out of the candidate.
3. Review the reconstructed candidate, saving the prompt, request metadata, raw response, returned model, verdict, and candidate hashes. The review must be read-only and have a parseable verdict.
4. Run focused tests and compile/diff checks against the same candidate bytes, not merely the current working tree. If the normal test harness cannot run outside the repo, use a temporary worktree or explicit import path; do not weaken production code to fit a stale fixture.
5. Immediately before staging, recompute hashes for every scoped file. If any current file differs from the reviewed candidate, stop: mark the evidence stale, re-read the current diff, rebuild the candidate from the new `HEAD`, rerun tests, and re-review.
6. Stage only the exact candidate paths/hunks. Verify `git diff --cached --name-status`, inspect the staged diff including removed lines, and ensure no pre-existing staged path entered the candidate.
7. After commit, verify `git show --name-status` and the committed content. After rebase, repeat final review/test because the tree may have changed.

## Common failure signatures

- `HEAD == origin/master` does not prove the worktree is unchanged; a concurrent writer can alter scoped files without committing.
- A prior `APPROVED` response is stale after any edit, fixture adjustment, line-ending rewrite, or same-file foreign hunk.
- A clean `git diff` can hide staged foreign work; always inspect `git diff --cached`.
- A wrapper's `Status: success` is not enough; read per-target `final_status`, `stop_reason`, and the artifact manifest.
- If reconciliation fails, preserve all dirty state and report `BLOCKED_AT_RECONCILIATION`; do not reset, clean, stash, or force-push.

## Minimal evidence record

```text
candidate_hashes: <path=sha256,...>
current_hashes_before_stage: <path=sha256,...>
review_route: <route/model>
review_verdict: APPROVED|REJECTED|BLOCKED
focused_tests: <command and real result>
staged_paths: <exact list>
foreign_dirty_paths: <preserved list>
```
