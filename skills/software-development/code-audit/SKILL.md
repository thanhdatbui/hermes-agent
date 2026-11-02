---
name: code-audit
description: "Proactive code audit — systematically inspect code for bugs across defined categories before they manifest. Find, fix, verify, and report."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-audit, bug-hunting, code-review, quality, static-analysis]
    related_skills: [systematic-debugging, requesting-code-review, code-review-response, test-driven-development]
---
# Code Audit

## Overview

Proactive code audit finds bugs before they manifest — no failing test, no user report, no PR review needed. Systematic inspection across defined categories catches what tests and linters miss.

**Core principle:** Audit from first principles — don't wait for a bug to crash. Read the code, trace the logic, identify what *could* go wrong, and fix it now.

## When to Use

Use when the user asks you to:

- "Audit this code" / "audit this function" / "review this code for bugs"
- "Check logic of X" with specific concerns (type safety, cleanup, edge cases, correctness)
- "Find bugs in" / "fix any issues in" a specific file or function
- "Kiểm tra kỹ logic" (check the logic carefully) + list of concern areas
- "Verify correctness" of new or changed code
- "Audit plan triển khai / đối chiếu invariants / cho verdict" — read-only audit of a Markdown implementation plan or design doc against acceptance criteria (invariants handoff, locked design) → see "Plan / Design-Doc Audit" below

**Don't use for:**

- Debugging an existing failure → `systematic-debugging`
- Pre-commit verification pipeline → `requesting-code-review`
- Responding to third-party review findings → `code-review-response`
- Metrics/statistics → `codebase-inspection`
- Project handoff review → `project-handoff-audit`

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
