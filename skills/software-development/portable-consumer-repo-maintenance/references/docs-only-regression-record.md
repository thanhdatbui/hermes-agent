# Documentation-only regression record

Use this reference when a repository task is intentionally limited to Markdown/docs and a handoff record, with no code, test, runtime, workbook, device, or artifact changes.

## Safe sequence

1. Confirm repository identity, branch, baseline SHA, remote, and dirty state. Treat unrelated dirty/untracked files as read-only.
2. Read the project instructions and the exact target docs. For a compatibility registry, enumerate existing `COMPAT-*` headings and choose a unique ID. Do not renumber historical entries merely because the registry already contains duplicates.
3. Capture the target files' byte-level EOL counts before editing. For CRLF files, use `read_bytes()`/`write_bytes()` or decode manually and re-encode with explicit CRLF; avoid text helpers that normalize newlines.
4. Add the smallest evidence-backed regression record. State the observed baseline, the regression signature, fallback ordering, safety boundary, post-action verifier, and the explicit prohibition that caused the regression. Keep evidence redacted and do not add runtime secrets or workbook data.
5. Recheck the final diff and scope. Stage only the named docs with explicit `git add <file> ...`; never stage the whole worktree.
6. Run `git diff --check` before commit and `git diff --check HEAD^ HEAD` after commit. For each changed file, assert `bare_LF == 0` and `bare_CR == 0` when CRLF is required.
7. Commit using the requested language. Push only the requested branch, then compare `git rev-parse HEAD` with `git ls-remote origin refs/heads/<branch>`.

## Reporting contract

Return:

- full commit SHA and commit subject;
- exact changed files;
- both diff-check results;
- per-file CRLF/LF/bare-ending counts;
- remote branch SHA confirmation;
- an explicit statement that tests were not run when the user prohibited code/test changes and the task is docs-only.

## Compatibility-entry checklist

A new `COMPAT-*` entry should preserve the established order: semantic known IDs first, generic compatibility fallback second, and legacy fallback flow third when still supported. Missing or malformed XML, and bounded dump failures such as exit 137, must not become a blocker when the fallback path has independent evidence and the field/flow is present. Keep the existing post-action visibility/content verifier. Do not promote exact-identity fail-closed behavior into live flow without multi-machine canary evidence.
