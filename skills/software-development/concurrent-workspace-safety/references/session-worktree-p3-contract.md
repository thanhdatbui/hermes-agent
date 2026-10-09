# Claude P3 Isolated-Worktree and Guarded-Write Contract

## Architecture Overview

When multi-agent orchestrations dispatch tasks to parallel workers, prompt allowlists fail to stop concurrent write collisions. The P3 contract defines a 3-layer fail-closed architecture:

1. **Physical Isolation**: Session worktree created under `.worktrees/<session_id>` on branch `p3/<session_id>` branched from a pinned commit SHA (`git rev-parse --verify <base_ref>^{commit}`).
2. **Worktree-Scoped Registry**: `SessionLeaseRegistry` initialized with `repo_root=worktree_canonical` and shared untracked storage under `.worktrees/.leases`. Any path leased must be relative to the worktree root.
3. **Pre-Write CAS Guard**: `guarded_write()` checks live lease ownership, canonical path identity, expiry safety margin, and base blob SHA match before atomic replace.
4. **Coordinator Integration**: Main branch integrates session branches via clean `fast-forward` or `rebase` (with automated `--abort` on conflict).
5. **Safe Cleanup**: Worktree removal strictly checks `registry.list()` for live leases (`LEASES_LIVE`), and executes `git worktree remove` without `--force`.

## Strict Containment Matrix (`validate_target_containment`)

`validate_target_containment(worktree, target, repo=None)` enforces six rejection boundaries:

| Condition | Return Code | Reason |
| :--- | :--- | :--- |
| `target == worktree` | `TARGET_IS_WORKTREE_ROOT` | Target cannot be the worktree directory itself |
| Target in main repo checkout | `TARGET_IN_MAIN_CHECKOUT` | Workers cannot write directly to main repository tree |
| Target in sibling worktree | `TARGET_IN_OTHER_WORKTREE` | Worktree cannot touch `.worktrees/<other_session>/...` |
| `.git` file, dir, or child | `TARGET_IS_GIT_METADATA` | Git metadata and hooks are protected from mutations |
| Symlink target resolves outside worktree | `SYMLINK_ESCAPE` | Symlinks cannot escape worktree boundary |
| Target outside worktree boundary | `TARGET_OUTSIDE_WORKTREE` | Arbitrary absolute or traversal paths are rejected |

## Base Blob SHA Standard

- **Absent target file**: `EMPTY_BLOB_SHA = hashlib.sha256(b"").hexdigest()` (`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
- **Existing target file**: `hashlib.sha256(path.read_bytes()).hexdigest()` (raw file bytes SHA-256).

## Key Implementation Pitfalls

1. **Git Worktree `.git` is a File**: In a git worktree, `.git` is a text file (`gitdir: ...`), not a directory. A check like `(path / ".git").is_dir()` fails on worktrees. Use `git rev-parse --git-common-dir` to discover the parent repository root.
2. **Finite TTL Arithmetic**: Calculating `ttl = max_write_duration + clock_skew_margin` can result in non-finite floats (`inf` from `1e308 + 1e308`) or raise `OverflowError`. Always validate `math.isfinite(ttl) and ttl > 0`.
3. **`OverflowError` Inheritance**: `OverflowError` in Python inherits from `ArithmeticError`, NOT `ValueError` or `OSError`. Any function validating numeric inputs must catch `OverflowError` explicitly or risk crashing uncaught on huge numbers.
4. **No `--force` on Cleanup**: Removing worktrees must use plain `git worktree remove <path>`. If dirty uncommitted files exist, git's built-in safeguard prevents silent data loss.
5. **Clean Abort on Rebase Conflict**: When integrating via `rebase`, detect non-zero exit codes immediately and run `git rebase --abort` to return the worktree and repository to an uncorrupted state before returning `REBASE_CONFLICT`.
6. **Integration Path Check & Checked-Out-Elsewhere Guard**: Before integration, verify `wt_path.exists()` (`WORKTREE_NOT_FOUND`). For fast-forward `update-ref` where target branch is not at root, verify against `git worktree list --porcelain` to reject if target branch is checked out in another worktree (`TARGET_BRANCH_CHECKED_OUT_ELSEWHERE`).
7. **Atomic `update-ref` with `old_sha` & Ancestry Gap Guard (B2 Fix)**: Read `old_sha` from root and `session_sha` from `wt_path` via a shared `_run_git()` helper before running `git merge-base --is-ancestor <old_sha> <session_sha>`. Do NOT re-resolve ref names after ancestry check. Run `git update-ref refs/heads/<target> <new_sha> <old_sha>`; if target moved in between, catch `subprocess.CalledProcessError` and return `TARGET_MOVED` instead of generic errors.
8. **Target Branch Not Checked Out at Root**: When target branch is not at root checkout (root is on another branch), fast-forward integration must check `git worktree list --porcelain`. If target branch is checked out in any other worktree, fail-closed with `TARGET_BRANCH_CHECKED_OUT_ELSEWHERE`. If not checked out elsewhere, perform atomic `update-ref` directly so the root working tree checkout remains on its own branch.
9. **Fail-Closed Branch Deletion**: In `cleanup_worktree()`, check the return code of `git branch -d`; if non-zero, return `BRANCH_DELETE_FAILED` instead of reporting successful cleanup.
10. **Automatic `.git/info/exclude` Hygiene**: On worktree creation, append `/.worktrees/` to `.git/info/exclude` in the main repo root to prevent worktree directories from appearing untracked without modifying tracked `.gitignore`.
11. **Case-Insensitive Git Metadata Containment**: Check `any(p.casefold() == ".git" for p in target_path.parts)` so Windows case-folded paths like `.GIT` or `.GIT/HEAD` cannot escape `TARGET_IS_GIT_METADATA` detection.

## Test Verification Matrix for Worktree Integration

| Test Case | Scenario | Expected Result |
| :--- | :--- | :--- |
| `test_coordinator_integration_fast_forward` | Root on target branch (`main`), worktree commits, fast-forward merge | `INTEGRATED`, working tree updated |
| `test_integrate_target_not_checked_out_at_root` | Root on branch `other`, worktree commits, target `main` updated via CAS `update-ref` | `INTEGRATED`, `main` ref updated, root stays on `other` |
| `test_integrate_target_checked_out_in_another_worktree` | Root on `other`, external worktree has `main` checked out | `TARGET_BRANCH_CHECKED_OUT_ELSEWHERE` |
| Fast-forward divergence | Target branch moved concurrently and is no longer ancestor of session branch | `FAST_FORWARD_CONFLICT` |
| Rebase conflict | Worktree and target branch have conflicting edits | `REBASE_CONFLICT`, clean `rebase --abort` |
