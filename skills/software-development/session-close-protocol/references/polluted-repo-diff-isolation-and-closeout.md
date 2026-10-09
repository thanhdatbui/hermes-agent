# Polluted Repo Diff Isolation and Closeout Recovery

## When to Use
Use when a closeout or session-close gate is rejected (e.g., score < 85/100, such as 27/100) due to massive repository diff contamination (e.g., 500–2,000+ files, hundreds of thousands of spurious insertions/deletions, unrelated regressions) while only a small, specific set of files was intended to be changed.

## Root Cause Signatures
1. **CRLF / Line-Ending Drift from Past Git Operations:**
   - On Windows, a past `git reset HEAD~1` (mixed reset) after a commit with CRLF conversion unstages hundreds of files with EOL modifications into the working tree.
   - Check with `git diff --ignore-space-at-eol --stat`: files showing 0 insertions/deletions under ignore-eol are pure line-ending churn.
2. **Checkout / Working Tree Staleness:**
   - Some working tree files are older versions predating `HEAD` (e.g., missing newer methods like batched helpers or execution tracking).
3. **Transient Compatibility Edits:**
   - Ad-hoc edits in unrelated modules (e.g., `conftest.py`, `moa_loop.py`) made solely to unblock local test runners must NOT be bundled into the feature closeout.

## Non-Destructive Isolation Protocol (The "Do No Harm" Rule)
1. **Never run destructive git commands on the active worktree:**
   - Do NOT run `git reset --hard`, `git checkout -- .`, or `git clean -fd`. The dirty worktree may contain active uncommitted work belonging to the user or other processes.
2. **Audit & Classify Every Target File:**
   - **Intended Feature Files:** Core logic + direct unit tests implementing the feature specification.
   - **Exclude Transitive / Compatibility Fixes:** If an edit was only made to compensate for a dirty/stale working tree file (e.g., adding `getattr(..., "clear")` because a local file was missing a cache dictionary present in clean `HEAD`), leave clean `HEAD` intact and omit the workaround.
   - **External Store / Config Files:** Note configuration or state changes outside the git repo (e.g., `jobs.json`).
3. **Extract Minimal Diff Against HEAD:**
   - Use `git show HEAD:<file>` as the canonical baseline.
   - Apply only the focused functional hunks onto the `HEAD` version.
   - Write out an isolated patch file (e.g., `split-session.patch`) in a temporary directory.
4. **Verify the Patch Artifact:**
   - Test application against clean HEAD index: `git apply --check --cached <patch>`.
   - Verify syntax: `python -m py_compile <isolated_files>`.
   - Verify test behavior: run focused tests using the isolated patch files in a separate directory or temporary worktree.
5. **Remediation Contract for Closeout Gate >= 85:**
   - Present the exact file list and diff stat of the isolated patch (e.g., 2 files, +104 / -5 lines vs 1,239 files).
   - Document excluded files and the reason for exclusion.
   - Provide the clean verification commands (e.g., `git worktree add -b feat/... ../clean-worktree HEAD` -> `git apply`) so the gate can achieve an approved score without corrupting the working tree.
