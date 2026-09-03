# Exclusive artifact-import verification

Use this pattern when a dirty shared repository already contains the exact artifacts that must be committed, but the implementation must occur in an exclusive worktree.

## Procedure

1. Capture the root status, HEAD, required parent/ref, existing worktrees, target path/branch, active writer processes, and SHA-256 of every allowlisted source artifact. Save the evidence outside the repository.
2. Create a fresh branch/worktree from the exact required parent. On Windows Git-Bash, inspect `git worktree list --porcelain` and `git -C <native-target> rev-parse --show-toplevel` immediately: `/d/...` arguments may create `D:\d\...`; remove only that self-created worktree and recreate with a native path such as `D:/Taadaa/...`.
3. Run the exact canonical combined test command before importing artifacts. This is the strict RED evidence. Do not manufacture RED with a per-file loop.
4. Re-check every source SHA-256 immediately before the first copy. If any differs from the baseline, stop for `SOURCE_DRIFT`; do not merge or overwrite.
5. Copy only the exact seven (or otherwise explicitly enumerated) allowlisted paths. Verify target hashes, LF/CRLF, BOM, and status. Keep pytest caches and ad-hoc scripts out of the worktree.
6. Run the exact combined suite for GREEN, then `py_compile`, hash/EOL/BOM checks, and `git diff --check`.
7. Stage exact paths only. Verify `git diff --cached --name-status` contains exactly the allowlist and no unrelated files. Commit, verify `git show --name-status --format=... HEAD`, and rerun focused/canonical checks post-commit.

## Immutable source caveat

If an adopted artifact is intentionally byte-for-byte and has existing trailing whitespace, preserve its bytes and hash. Report the exact `git diff --check` warning as a known pre-existing artifact issue, run `git diff --check` excluding that immutable path, and require PASS for every other scoped artifact. Do not claim a blanket diff-check pass when the immutable warning remains.

## Evidence labels

Distinguish `RED` (canonical suite before import), `GREEN` (after import), `POST_COMMIT_GREEN`, and compile/hash/EOL checks. Report the commit SHA, exact file count, parent SHA, clean target status, and unrelated root dirty paths separately. Never claim the root remained unchanged unless tracked status, untracked path set, and any HEAD movement were all independently reconciled.
