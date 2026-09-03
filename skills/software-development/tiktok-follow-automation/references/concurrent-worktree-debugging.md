# Concurrent worktree and dirty-file safety for follow fixes

When a follow incident is reported with a screenshot or runtime error, source changes must be global and test-backed, but a dirty/shared worktree is evidence of ownership risk—not permission to overwrite.

## Required checkpoint before editing

1. Run the repository bootstrap gate and capture `HEAD`, branch, clean/dirty state, and the exact allowlist.
2. Inspect both `git diff` and `git diff --cached`; record pre-existing staged and unstaged paths separately.
3. Read the complete target file immediately before patching. Partial/paginated reads are not sufficient for whole-file replacement.
4. If a target file is modified by another worker/process after the read checkpoint, stop source edits with `SCOPE_CONFLICT`. Do not `reset`, `checkout`, revert, normalize line endings, or overwrite the overlapping file.

## Regression-test insertion rule

Add the smallest fixture reproducing the exact UI classification failure. Keep the test function structurally intact: after an insertion, re-read the surrounding region and confirm that no existing test body or `def` declaration was displaced. If a concurrent writer changes the same test file, treat any passing subset as `VERIFIED_CURRENT_TREE` only—not proof that this fix was safely applied.

## Verification labels

- `FIX_COMPLETE`: only when the intended production/test patch is attributable to the current task and focused tests pass on the final bytes.
- `SCOPE_CONFLICT`: concurrent edits/ownership overlap stopped implementation.
- `VERIFIED_CURRENT_TREE`: tests pass on the current tree after conflict, but the requested patch is not attributable or safe to claim complete.
- `BLOCKED`: required runtime/live evidence or target resolution is missing.

Keep incident reports concise: purpose → result → blocker. Never claim a live fix, commit, or push from a worker summary or a partial test run. Preserve unrelated dirty changes and report exact conflicting paths.

See `references/concurrent-worktree-debugging.md` for the reusable checkpoint and evidence format.
