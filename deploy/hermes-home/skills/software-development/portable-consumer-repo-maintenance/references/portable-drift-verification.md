# Portable Drift Verification Notes

## Proven verification shape

For a Python consumer repo whose changed scripts are under a worktree, use a temporary script under the OS temp directory with a `hermes-verify-` prefix. Run it with the worktree on `PYTHONPATH`:

```bash
PYTHONPATH='D:/path/to/worktree' python 'C:/Users/<user>/AppData/Local/Temp/hermes-verify-example.py'
status=$?
rm -f 'C:/Users/<user>/AppData/Local/Temp/hermes-verify-example.py'
exit $status
```

The check should import the actual parser/default definitions and assert:

- defaults exclude known host-specific fragments such as `OneDrive`, `CodexRuntime`, cache roots, and user-profile paths;
- environment variables populate defaults when flags are absent;
- explicit CLI flags still win over defaults;
- PowerShell installer text contains no flagged absolute paths and includes the supported override names.

Expected success output should be a concise marker such as `AD_HOC_PORTABLE_DEFAULTS_VERIFIED`. Confirm the temporary file is removed. Report this as **ad-hoc verification**, not as a canonical suite result.

## Failure classification

- Import failure from `%TEMP%`: rerun with `PYTHONPATH=<worktree>`; do not misclassify as a product failure.
- Full-suite failures involving missing sibling/reference worktrees or stale fake fixtures are baseline/environment blockers unless they touch changed files.
- A Windows worktree naturally has a drive-letter absolute representation. Reject machine identity fragments, not all drive letters.
