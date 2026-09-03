# Closeout review of a moving candidate (concurrent writer), 2026-08-23

Session: read-only APPROVED/REJECTED/BLOCKED closeout review of 5 in-scope files
(`benign_popup.py`, `feed_swipe_smoke.py` + 3 test files) while another writer
was actively mutating the same worktree.

## Timeline of mutations observed

1. Review started on unstaged diffs (` M`) → full diff read completed.
2. Next `git diff` returned EMPTY → files had been STAGED (`M `) by the writer
   between calls. Recovered by switching to `git diff --cached`.
3. Mid-review everything was UNSTAGED again and `requirements-automation-core.txt`
   went dirty (wheel bump 0.4.45→0.4.46, out of scope).
4. HEAD then MOVED: writer committed the candidate as
   `6dfd722 fix(feed): harden profile verification and popup handling`.
5. Commit was slightly LARGER than the staged diff previously read
   (test_feed_session_smoke 9→11 lines, test_feed_swipe_smoke 109→127):
   two additive test-only hunks (one new fail-closed artifact test +
   artifact-validator patches). Production blobs unchanged (identical ± stats).
6. One pytest run FAILED 2 focus-loss tests; seconds later the uncommitted
   production mutation it raced had been reverted (`git diff` empty again).
   Re-verified clean vs HEAD → same 2 tests passed → attributed to racing the
   transient mutation, not a regression.

## Heuristics that worked (use next time)

- **Empty diff ≠ no changes.** `git diff <paths>` empty + files still listed
  dirty in `git status` ⇒ read `git diff --cached`. Always re-snapshot
  `git status --porcelain` + `git log -1` after any anomalous result.
- **Rebind on HEAD move.** `git show <sha> --stat` → compare per-file ± counts
  to the diff you reviewed; pull and review ONLY the delta hunks
  (`git show <sha> -- <path>`); confirm production blobs unchanged when stats
  match exactly. Verdict then applies to the SHA, not to the lost worktree state.
- **Bind evidence to bytes.** After any candidate change, re-run focused suites
  on the final bytes before reporting. Marker greps against the SHA are cheap:
  `git grep -c "<symbol>" <sha> -- <path>`.
- **False failures from races.** Failing run + later-empty diff ⇒ suspect a
  reverted transient mutation: verify clean-vs-SHA, re-run, report both the
  false failure and its cause.
- **Preserve out-of-scope dirt.** Pre-existing dirty files (PROJECT_RULES.md,
  multi_machine_feed_session.py) stayed untouched throughout; newly appearing
  out-of-scope dirt (requirements wheel bump) is flagged for owner decision,
  not reviewed.
- **Empty model turn after tool calls:** just re-issue one cheap re-check
  command (`git log -1 && git status --porcelain`) and continue.

## Commands that produced valid evidence (Windows git-bash)

```bash
cd "/d/Taadaa/tiktok-luot nuoi acc"
git status --porcelain=v1 && git log --oneline -1
git diff --stat -- <in-scope paths>            # empty + dirty ⇒ staged
git diff --cached -- <in-scope paths>
git show <sha> --stat | tail -10
git grep -c "<marker>" <sha> -- python_runner/flows/feed_swipe_smoke.py
python -B -m compileall -q python_runner/flows/benign_popup.py python_runner/flows/feed_swipe_smoke.py
git diff --check HEAD
# NOTE: quoted MSYS paths + leading "." for repo-root imports of flows/core:
PYTHONPATH=".;/d/Taadaa/tiktok-luot nuoi acc;/d/Taadaa/tiktok-luot nuoi acc/python_runner" \
  python -B -m pytest -q -p no:cacheprovider \
  python_runner/tests/test_benign_popup.py python_runner/tests/test_feed_swipe_smoke.py
# test_feed_session_smoke.py alone takes ~4.5 min (263s) — budget for it.
```

## Result

APPROVED at 6dfd722: import fix verified at definition site, fail-closed
profile-anchor + artifact-first contract matched the skill's code-fix
regression pattern, no unsafe recovery added, 151+170 passed / 11 skipped on
final bytes, out-of-scope files preserved.
