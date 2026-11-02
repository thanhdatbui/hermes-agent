---
name: delegate-windows-farm-repo
description: Pitfalls and correct pattern when delegating build/commit tasks to subagents that must edit the Taadaa Windows farm repo (D:\Taadaa\tiktok-luot nuoi acc). Prevents silent no-op writes and HEAD-drift aborts.
---
# Delegating to subagents on the Windows farm repo

See `references/guard-contract-and-repo-whitelist.md` for Scope Lock formatting, repo whitelist invariants (`OUT OF REPO WHITELIST`), file count limits, and Coordinator T1 budget rules.

Use when dispatching `delegate_task` workers that must write/commit to
`D:\Taadaa\tiktok-luot nuoi acc` (or sibling worktrees). Two recurring
failure modes have burned real retries.

## Pitfall 1 — worker writes don't land in target
Delegated worker terminals START at `/c/Users/Kibe`, NOT in the repo.
If the worker does not `cd` into the repo first, any file it "writes"
lands nowhere the parent can see. The worker may then report
"ad-hoc verification PASS" / "APPROVED" while `git status` on the
target shows zero changes.

**Mandatory instruction block for every delegate_task that edits the repo:**
- "Before EVERY shell command run `cd /d/Taadaa/tiktok-luot nuoi acc`
  first. Use POSIX path `/d/Taadaa/tiktok-luot nuoi acc` for all shell
  commands and file writes; do NOT use `D:\\...` in shell."
- "Before editing, inspect `git status --short` and the scoped `git diff`; preserve unrelated dirty hunks."
- "Keep edits to the explicitly named files and run every required verification command before claiming completion."
- "Report exact files modified, real test output, and any verification that could not run; never claim DONE without it."
  first. Use POSIX path `/d/Taadaa/tiktok-luot nuoi acc` for all shell
  commands and file writes; do NOT use `D:\...` in shell."
- "Before final report, in the SAME terminal run:
  `cd /d/Taadaa/tiktok-luot nuoi acc && grep -n '<marker>' <file> &&
  test -f <newfile> && python -B -m pytest ... && git status --short &&
  git diff --name-only`. If the marker/file is absent or diff is empty,
  do NOT report completion."
- Point workers at the EXACT absolute target; do not let them guess or
  clone. Existing sibling worktrees:
  `D:/Taadaa/tiktok-luot-nuoi-acc-scheduler-phase8-wt`,
  `D:/Taadaa/tiktok-luot-nuoi-acc-recovery-adapter-p1-wt`.

## Pitfall 2 — origin/master drift aborts workers
A background fetch/pull advances `origin/master` to unrelated policy
commits (e.g. `1146c20`). Local `master` lags. A worker told to expect
a specific HEAD (e.g. `6696e6b` or `1146c20`) will STOP on mismatch —
even though the Phase-9 commits are still ancestors of the drifted HEAD
(no history is lost).

**Reconciliation (do NOT reset/checkout to origin):**
1. `git merge-base --is-ancestor <drifted-origin-sha> HEAD` → if YES,
   all phase commits are intact.
2. Commit the new phase on CURRENT local HEAD (add one commit on top),
   never `git reset`/`checkout`/`pull` to origin.
3. Verify with `git show --stat --oneline <newsha>` and re-run the
   canonical pytest suite.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
