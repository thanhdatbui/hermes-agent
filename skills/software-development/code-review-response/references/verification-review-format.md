# Verification Review Format

Use this template when producing a criteria-based verification review — verifying code against explicit behavioral/design requirements.

## Full Template

```markdown
## Verification Review: [topic]

### Checklist

| # | Criterion | Expected | Actual | Status |
|---|-----------|----------|--------|--------|
| 1 | Core flow runs before fallback | `open_profile_root()` called first | Line 714: first action in retry loop | ✅ PASS |
| 2 | Fallback doesn't replace core | Core call unconditional | No conditional gate before line 714 | ✅ PASS |
| 3 | Fallback fail → escalation | MANUAL_REVIEW with instructions | Lines 740-757: `is_ui_unavailable=True`, detailed message | ✅ PASS |
| 4 | No fabricated success | success=True only on real success | Line 737: `profile_success=True` after verified fallback | ✅ PASS |
| 5 | No automation-core changes | No diffs in shared library | git diff shows 0 changes in automation-core/ | ✅ PASS |

### Build Verification

| Check | Result |
|-------|--------|
| pytest | 92/92 passed |
| Compile | OK (py_compile) |
| Import | OK |

### Minor Findings

- **Finding 1** — non-blocking, suggestion only
- **Finding 2** — minor issue, not blocking

### Decision

**✅ APPROVED** — All criteria met. Ready for merge.
```

## Lightweight Template (for quick reviews)

```markdown
## Verification Summary

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Core before fallback | ✅ | Line 714 |
| 2 | No fabricated success | ✅ | Line 737 |
| 3 | MANUAL_REVIEW on total fail | ✅ | Lines 740-757 |

### Build
- pytest: N/N passed
- compile: OK
- import: OK

### Decision
**✅ APPROVED**
```

## Field Guidance

| Field | How to fill |
|-------|-------------|
| **Criterion** | Exact wording from the user's requirement, or paraphrased if clearer |
| **Expected** | What the code *should* do according to the requirement |
| **Actual** | What the code *does* — cite specific line numbers |
| **Status** | ✅ PASS / ❌ REJECT / ⚠️ MINOR |

## Status Rules

- **PASS** — code does exactly what the criterion requires
- **REJECT** — code does NOT meet the criterion; blocks approval
- **MINOR** — meets the criterion but has a non-blocking flaw (redundancy, missing test, brittle coordinates)
- **N/A** — criterion does not apply

## Decision Rules

| All PASS? | Any MINOR? | Any REJECT? | Verdict |
|:---------:|:----------:|:-----------:|---------|
| ✅ Yes | No | No | **APPROVED** |
| ✅ Yes | Yes | No | **APPROVED (MINOR_FIXES)** — address minors before merge |
| ❌ No | — | No | **PARTIAL_APPROVAL** — PASS items mergeable, remaining need next cycle |
| ❌ No | — | Yes | **REJECT** — at least one criterion failed; needs rework |
