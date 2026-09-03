# Canonical `--resume` entrypoint dispatch smoke check

## Why this matters

A live `social_reg_v1.py <stt> --resume` run can return exit code `0` after lock/preflight and still never execute the resume body. Syntax compilation does not catch this class of structural bug.

## Read-only verification recipe

1. Read the exact source around:
   - `if __name__ == "__main__":`
   - `_resume_read_mailbox_then_return_to_tiktok(...)`
   - the `try:` that should contain `if "--resume" in args:`
   - the final `register(...)` path.
2. Confirm indentation/AST ownership: the resume `try:` must be inside the `__main__` block, not inside a helper function defined after the block began.
3. Run `py_compile` only as a syntax check; do not treat it as dispatch proof.
4. Redirect stdout/stderr to a per-target log without `| tail`.
5. Require at least one of:
   - `[resume]` or `[resume-dbg]`
   - `[otp-gmail]`, `[otp-reader]`, canonical Outlook reader/magic-link evidence
   - explicit `STOPPED`, `ERROR`, or fail-closed result.
6. If the log ends at `[init] device readiness`, classify `ENTRYPOINT_DISPATCH_NOT_REACHED` and stop the mailbox claim. Do not infer the newest-mail category from foreground app, exit `0`, or the absence of an exception.

## Remediation boundary

If this smoke check finds a structural no-op, do not work around it with a custom mailbox script, `monkey`, external Gmail/Chrome launch, or a different entrypoint. The canonical source must be corrected through the repository's authorized change workflow, then independently verified before another live run.
