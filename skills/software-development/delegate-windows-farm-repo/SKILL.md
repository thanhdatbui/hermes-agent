---
name: delegate-windows-farm-repo
description: Pitfalls and correct pattern when delegating build/commit tasks to subagents that must edit the Taadaa Windows farm repo (D:\Taadaa\tiktok-luot nuoi acc). Prevents silent no-op writes and HEAD-drift aborts.
---

# Delegating to subagents on the Windows farm repo

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

## Verification gate (always, regardless of worker self-report)
- Ad-hoc `hermes-verify-*.py` temp scripts are NON-EVIDENCE. Only the
  canonical `python -B -m pytest -q -p no:cacheprovider <exact suite>`
  counts as proof.
- Independently run: focused test(s) → exact R5 regression suite →
  `python -m py_compile` → `git diff --check` → `git show` on the new
  commit, BEFORE trusting any "APPROVED"/"PASS".
- Commit only after AG Opus (ag/claude-opus-4-6-thinking via 9Router
  localhost:20128) returns first-line APPROVED. Do not commit on worker
  self-report.
- Stage ONLY the phase allowlist paths; never stage pre-existing dirty
  files (AGENTS.md, HANDOFF.md, PROJECT_RULES.md, scripts/*, untracked
  plan/generator drafts).

## Pattern: Sync docs+commits across both farm repos (automation-core + tiktok-luot nuoi acc)

When the user asks to update a shared doc (e.g. `docs/farm-automation-cases.md`) and commit on **both** repos:

1. **Read both files first** to confirm current tail and EOL style:
   ```bash
   cd /d/Taadaa/automation-core && tail -20 docs/farm-automation-cases.md
   cd "/d/Taadaa/tiktok-luot nuoi acc" && tail -20 docs/farm-automation-cases.md
   ```
   - automation-core uses **CRLF** (1053 CRLF, 0 lone LF)
   - tiktok-luot nuoi acc uses **LF** (0 CRLF, 892 LF)

2. **Write the update via a Python script file** (not terminal heredoc) to avoid:
   - MSYS path mangling (`/d/` vs `D:\`)
   - f-string backslash SyntaxError with byte literals
   - Terminal `&&` backgrounding guard rejection
   ```python
   # script: update_docs_caseXX.py (place in user home, NOT in repo)
   with open(ac_path, "rb") as f: ac_orig = f.read()
   ac_block = b"\r\n---\r\n\r\n" + b"\r\n".join([l.encode("utf-8") for l in lines]) + b"\r\n"
   with open(ac_path, "wb") as f: f.write(ac_orig + ac_block)
   
   with open(tt_path, "rb") as f: tt_orig = f.read()
   tt_block = b"\n---\n\n" + b"\n".join([l.encode("utf-8") for l in lines]) + b"\n"
   with open(tt_path, "wb") as f: f.write(tt_orig + tt_block)
   ```

3. **Verify EOL preserved** after write:
   ```bash
   python3 -c "
   with open('D:/Taadaa/automation-core/docs/farm-automation-cases.md', 'rb') as f:
       d = f.read(); print('AC CRLF:', d.count(b'\r\n'), 'lone LF:', d.count(b'\n') - d.count(b'\r\n'))
   with open('D:/Taadaa/tiktok-luot nuoi acc/docs/farm-automation-cases.md', 'rb') as f:
       d = f.read(); print('TT CRLF:', d.count(b'\r\n'), 'lone LF:', d.count(b'\n') - d.count(b'\r\n'))
   "
   ```

4. **Stage + commit each repo with Vietnamese commit message** (user convention):
   ```bash
   cd /d/Taadaa/automation-core && git add docs/farm-automation-cases.md <changed_src> <changed_tests> && git commit -m "feat(...): ... (Case XX)"
   cd "/d/Taadaa/tiktok-luot nuoi acc" && git add docs/farm-automation-cases.md <changed_src> <changed_tests> && git commit -m "feat(...): ... (Case XX, Machine YY)"
   ```

5. **Run canonical pytest on both repos** as verification gate:
   ```bash
   cd /d/Taadaa/automation-core && pytest -q
   cd "/d/Taadaa/tiktok-luot nuoi acc" && pytest -q python_runner/tests/test_<relevant_suite>.py
   ```

6. **Report both commit hashes + stats** for traceability:
   ```
   | Repo | Commit Hash | Commit Message |
   |------|-------------|----------------|
   | automation-core | e773c58 | feat(popups): ... (Case 75) |
   | tiktok-luot nuoi acc | 296dff4 | feat(popups): ... (Case 75, Machine 52) |
   ```
