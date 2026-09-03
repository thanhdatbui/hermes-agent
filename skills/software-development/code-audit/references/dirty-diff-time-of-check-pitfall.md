# Dirty-Diff Audit: Time-of-Check vs Time-of-Use (worktree mutates mid-review)

## When this bites
You are reviewing an UNCOMMITTED change (read-only diff audit). Your job: issue
APPROVED/BLOCKED (or the verdict vocabulary the user named) against the current
dirty worktree. Between your first `git diff` capture and your final verdict, the
worktree can change out from under you: the user (or another process / cron /
other agent) can `git commit`, `git stash`, `git checkout`, `git commit --amend`,
or `git pull`. Your verdict would then cite a snapshot that no longer exists.

## Worked case (2026-08-22, `D:\Taadaa\tiktok-luot nuoi acc`)
- Opening `git status` showed 9 modified files, uncommitted.
- Initial `git diff python_runner/core/classifier.py` showed ~25 changed lines,
  INCLUDING a newly ADDED captcha-puzzle-close branch (`detect_captcha_puzzle_close`
  import + a new `manual-needed:popup` return) and a new test
  `test_dismissable_captcha_with_close_x_is_popup_not_manual_challenge`.
- Mid-review, a later `git status` returned **"nothing to commit, working tree
  clean"**, and `git reflog` showed
  `4a70ed6 HEAD@{0}: commit: fix(classifier): remove signup false-positive login overlay mechanism`.
- The COMMITTED diff differed materially from the uncommitted snapshot:
  classifier.py shrank to 15 lines and the captcha-puzzle-close branch + its test
  were GONE (stripped before commit).
- Had the verdict cited the in-progress captcha branch, it would have described
  code that no longer existed.

## Mitigation (mandatory before verdict)
1. Immediately before composing the verdict, RE-RUN the git state capture:
   - `git status --short`
   - `git diff --stat`
   - `git diff -- <named files>` (the exact files you reviewed)
2. If the tree is now CLEAN but a new commit exists, switch to a commit-scoped audit:
   - `git log --oneline -3` and `git reflog -8` to find the commit
   - `git show <commit>` / `git diff-tree --no-commit-id --name-status -r <commit>`
     to audit the committed blobs (see "Commit-Scoped Phase Acceptance Audit")
3. Confirm the final-state diff == the diff you actually analyzed. If they differ,
   RE-VERIFY the new content and RE-RUN the scoped tests against the final state
   before issuing the verdict.
4. Never cite a branch/symbol/line that isn't present in the final
   committed-or-dirty state. If your notes reference removed code, say so
   explicitly and re-derive the finding from the current blobs.

## Symptom quick-check
If at any point your `git diff` for a file suddenly returns EMPTY but `git status`
earlier showed it modified → the tree was committed/reset. Stop, re-baseline,
re-verify. Do not continue from stale notes.
