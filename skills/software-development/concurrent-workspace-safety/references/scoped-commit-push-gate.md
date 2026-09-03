# Scoped Commit/Push Gate in a Dirty Shared Worktree

Use this when a worker has already edited the requested files, the repository contains unrelated dirty and untracked content, and the user requires a narrow commit plus push.

## Checklist

```bash
# Read-only baseline
pwd
git status --short --untracked-files=all
git diff --name-status
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
git diff -- <scoped-files>
stat -c '%y %n' <scoped-files>

# Focused verification; exact node IDs avoid pytest -k matching the module filename
python -m pytest -q tests/test_module.py::test_timeout_behavior tests/test_module.py::test_default_wait
python -m py_compile <production.py> <test.py>
git diff --check

# Scope guard
 git add -- production.py helper.py tests/test_module.py
git diff --cached --name-status
git diff --cached --check

git commit -m '<requested-language fix message>'
git show --format='SHA=%H%nSUBJECT=%s' --name-status HEAD
git push <remote> <branch>
git ls-remote <remote> refs/heads/<branch>

# Post-commit proof
python -m pytest -q tests/test_module.py::test_timeout_behavior tests/test_module.py::test_default_wait
python -m py_compile <production.py> <test.py>
git diff --check HEAD^ HEAD -- <scoped-files>
git diff --cached --name-only
```

Do not use `git add .`, `git add -A`, checkout/revert, or cleanup commands in this workflow. A broad test module may contain an unrelated baseline failure; record it separately from the exact fix-specific green tests and do not edit foreign work to make the broad module green. If the status output is huge, redirect porcelain status to a file outside the repository and report tracked/untracked counts plus top-level groups; keep the full manifest available for audit.

## Reporting template

- **Commit:** full SHA and requested-language subject.
- **Files:** exact `git show --name-status` list; confirm the index is empty.
- **Focused tests:** exact command and pass count.
- **Broader tests:** exact command and any pre-existing/unrelated failure, without calling the suite green.
- **Checks:** `py_compile`, committed diff check, working-tree diff check.
- **Push:** remote/branch, command result, and `git ls-remote` SHA.
- **Remaining dirty state:** tracked count/list, untracked count/top-level groups, and path to the outside-repo manifest.
