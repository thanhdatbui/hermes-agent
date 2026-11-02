---
name: portable-consumer-repo-maintenance
description: "Implement focused consumer-repository fixes for machine-specific configuration drift with isolated worktrees, override preservation, and evidence-based verification."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [consumer-repo, portability, configuration-drift, worktree, verification]
    related_skills: [systematic-debugging, test-driven-development, requesting-code-review]
---
# Portable Consumer-Repo Maintenance

## Trigger

Use when a consumer repository has machine-specific absolute paths, runtime defaults, scheduler/install wrappers, or configuration drift findings. This applies to Python, PowerShell, shell, and mixed-language workflow entrypoints.

## Documentation-only regression records

When the requested change is a compatibility-regression record limited to repository docs/handoff (no code, tests, runtime, workbook, or device changes), use this narrower path:

1. Snapshot repository identity with `git status --short --branch`, `git rev-parse HEAD`, remote URL, and the exact target files. Preserve unrelated dirty/untracked state.
2. Inspect the compatibility registry's existing `COMPAT-*` IDs before adding an entry. Choose a unique new ID; do not renumber or rewrite unrelated historical duplicates.
3. Preserve byte-level EOL. For CRLF-sensitive Markdown, edit with bytes or explicit `read_bytes()`/`write_bytes()` and verify no bare LF/CR after the final edit.
4. Stage only explicit target paths, never `git add .`; run `git diff --check` before commit and against `HEAD^` after commit.
5. Commit with the user's requested language, push only the requested branch, and independently verify the remote branch SHA.
6. Return the full commit SHA, exact changed files, both diff-check outcomes, EOL counts, and state clearly when tests were intentionally not run because they are outside the authorized docs-only scope.

For the reusable command/report checklist, see `references/docs-only-regression-record.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
