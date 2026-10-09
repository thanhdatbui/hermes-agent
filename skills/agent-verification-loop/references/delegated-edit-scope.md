# Bounded delegated-edit verification

Use this reference for narrowly scoped code edits where the coordinator specifies exact files, diff limits, and test commands.

## Before editing

1. Use the repository path explicitly provided by the coordinator; do not substitute a container-style path.
2. Inspect `git status`, the target diff, and the target test file's raw bytes. Record CRLF/LF counts and encoding when line-ending preservation is part of the task.
3. Confirm dependency/test entry points before adding imports or mocks.

## Edit discipline

- Apply a targeted patch; never rewrite a whole test file to append one regression test.
- Keep production and test additions inside the stated line/file budget.
- For canary/startup regressions, test the observable contract: no prompt, startup methods before hook, cleanup/dismissal ordering, direct row/account binding, and emitted result.

## Verification gate

Run the new pytest node before the production change when feasible (RED), then rerun it after the minimal fix (GREEN). Run the requested focused file afterward. Finish with `git diff --numstat` and `git diff --check`; re-count raw newlines in protected test files. If a tool-call or execution budget is closing, prioritize applying the requested production patch and focused verification over polishing or expanding the test. Report any unperformed verification explicitly; never present a draft or partial test as a completed fix.
