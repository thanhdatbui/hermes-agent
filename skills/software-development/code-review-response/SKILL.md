---
name: code-review-response
description: Respond to code review findings (especially critical/P0 issues). Implement fixes, verify with tests, and ensure no regressions.
triggers:
  - code review feedback
  - P0 critical issues
  - review findings
  - Claude review
  - fixing review comments
  - fix re-review
  - verify fixes applied
  - re-review findings
  - verify criteria
  - verification review
  - check requirements
  - compliance review
---
# Code Review Response

Systematic approach to fixing critical issues identified in code review.

## When to Use

- Received code review with P0/critical issues
- Need to implement reviewer-suggested fixes
- Must verify fixes don't introduce regressions

## Severity-Based Triage

Review findings come in severity tiers. Handle in strict priority order:

| Tier | Label | Action |
|------|-------|--------|
| 🔴 Critical | Blocking, security, data loss, TODO stubs | Implement immediately |
| 🟠 High | Correctness, major API misuse, private API access | Fix after critical, before medium |
| 🟡 Medium | Style, dead code, minor patterns, doc/import hygiene | Auto-fix in batch after everything else |

For each tier, read all findings first, then batch independent fixes across files.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
