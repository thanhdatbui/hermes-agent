# Scoped repository cleanup after explicit user authorization

Use this reference when the user explicitly authorizes cleanup of a named repository and says to ask only about important items. This procedure applies to repository state only; it does not authorize live/device actions, ADB, cron changes, workbook edits, credentials, unrelated repositories, or remote-history changes.

## Contract

- **Goal:** leave the named repository clean while preserving anything materially important.
- **In scope:** dirty working-tree paths, local-only commits, stale plans, generated artifacts, and backups in that repository.
- **Ask before acting:** live-behavior changes, user-authored policy/data, secrets/configuration, uncertain artifacts, or any remote push.
- **Acceptance:** empty porcelain, no staged/unstaged diff, `git diff --check` passes, one intended worktree, and local `HEAD` equals the tracked upstream (0/0 ahead/behind).

## Evidence-first workflow

1. Record the baseline outside the repository:

   ```bash
   git status --short --untracked-files=all
   git branch --show-current
   git rev-parse HEAD
   git rev-parse --abbrev-ref --symbolic-full-name '@{u}'
   git rev-list --left-right --count HEAD...@{u}
   git log --oneline @{u}..HEAD
   git diff --name-status @{u}..HEAD
   git diff --binary > <external-backup>/pre-cleanup-diff.patch
   ```

2. Inspect all local-only commits as an aggregate diff, not only commit messages. For generated AI recovery commits, check:
   - whether the changed symbols are registered in the relevant registry;
   - whether they are imported or called anywhere;
   - whether focused tests cover them;
   - whether the diff is append-only and repeatedly touches one file;
   - whether the file contains duplicate function definitions or incompatible API styles.

   Strong evidence of disposable generated junk is: many one-file append-only commits, duplicate definitions, no registration, no caller, and no focused tests. A commit message claiming audit/pytest approval is not proof of importance.

3. Back up every item to be deleted or discarded outside the repo. Include a manifest with path, size, and SHA-256. Save the pre-cleanup status, text/binary diff, and local-only commit list too. Do not place the backup under the worktree.

4. Clean narrowly:
   - restore reviewed tracked documentation noise to `HEAD`;
   - remove only reviewed stale plans, generated reports, and obsolete backups;
   - if every local-only commit is proven disposable, fetch the upstream and reset the local branch to that upstream ref;
   - do not push merely because local history was cleaned.

   Never use `git add .`, broad `git clean`, or an unclassified `git reset --hard`.

5. Verify after cleanup:

   ```bash
   test -z "$(git status --porcelain=v1 --untracked-files=all)"
   git diff --exit-code
   git diff --cached --exit-code
   git diff --check
   test "$(git rev-list --left-right --count HEAD...@{u})" = '0\t0'
   git worktree list --porcelain
   ```

   If production code was retained or changed rather than restored to upstream, run the focused test and compile gates before reporting success.

## Reporting

Report briefly: repository, clean/dirty result, local/remote relationship, what was discarded by category, what was preserved, external backup path, and whether anything was pushed. Do not claim that remote history changed unless `git ls-remote` verifies it.
