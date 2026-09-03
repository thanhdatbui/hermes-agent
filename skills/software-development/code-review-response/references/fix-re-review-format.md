# Fix Re-Review Verdict Template

Use this template when re-reviewing fixes applied by another contributor after an initial code review. Copy, fill the sections, and present to the user.

```markdown
---

## 📋 RE-REVIEW: KẾT QUẢ

### 1️⃣ Tổng quan

| Finding | Verdict | Ghi chú |
|---------|---------|---------|
| 🔴 C1 — <title> | ✅ **APPROVED** | <explanation> |
| 🔴 C2 — <title> | ✅ **APPROVED** | <explanation> |
| 🟠 H1 — <title> | ✅ **FIXED** | <explanation> |
| 🟡 M1 — <title> | ✅ **FIXED** | <explanation> |
| — | ⚠️ **MINOR** | <dead code / nit found during re-review> |

### 2️⃣ Verification tests

```
✅ python -c "from project.module import Symbol; print('OK')"
✅ python -c "import project; print('OK')"
✅ python -m pytest tests/ -v → N/N passed
```

### 3️⃣ Minor issues phát hiện thêm

<if any, list new issues found during re-review that weren't in the original findings>

### 4️⃣ Kết luận

## ✅ **APPROVED** (MINOR_FIXES)
```

## Verdict definitions

| Verdict | Meaning |
|---------|---------|
| **APPROVED** | Fix is correct, robust, and matches the expected pattern. No issues. |
| **MINOR** | Fix is functionally correct but has a cosmetic issue (dead code, unused import, stale comment). Not blocking. |
| **FIXED** | Finding is resolved. Used for non-critical tiers (🟠 High, 🟡 Medium). |
| **REJECT** | Fix does not address the finding or introduces worse issues. Must redo. |
| **PARTIAL** | Some items approved, some rejected. Manual triage needed. |

## Severity prefixes from original review

| Prefix | Original Tier | Examples |
|--------|--------------|----------|
| 🔴 C | Critical | TODO stubs, security, data loss |
| 🟠 H | High | Correctness, private API access, major misuse |
| 🟡 M | Medium | Dead code, style, import hygiene |

## Output format variants

### Short (for clean passes)
```
## Re-Review Verdict: ✅ APPROVED

| Finding | Verdict |
|---------|---------|
| 🔴 C1 | ✅ APPROVED |
| 🔴 C2 | ✅ APPROVED |
| 🟠 H1 | ✅ FIXED |
| 🟡 M1 | ✅ FIXED |

All 4 findings resolved. 68/68 tests pass. No regressions.
```

### With MINOR items
```
## Re-Review Verdict: ✅ APPROVED (MINOR_FIXES)

| Finding | Verdict | Notes |
|---------|---------|-------|
| 🔴 C1 | ✅ APPROVED | Multi-strategy fallback with verify |
| 🟡 M3 | ✅ FIXED | Returns False, detects CAPTCHA |
| — | ⚠️ MINOR | Variable `escaped` assigned but unused (file.py:42) |

68/68 tests pass. The minor item does not block merge.
```

### With rejection
```
## Re-Review Verdict: ❌ REJECT

| Finding | Verdict | Notes |
|---------|---------|-------|
| 🔴 C1 | ✅ APPROVED | Looks good |
| 🟠 H2 | ❌ REJECT | `adb.run()` called but only `adb.shell()` exists on API — fix will crash at runtime |
| 🟡 M4 | ✅ FIXED | |

C2 must be re-fixed. C1 and M4 can merge independently.
```

## Finding ID convention

When creating the checklist for re-review, follow this ID scheme:

- **C** = Critical (🔴) — from the original review's critical tier
- **H** = High (🟠) — from the original review's high tier  
- **M** = Medium (🟡) — from the original review's medium tier

Number sequentially within each tier (C1, C2, H1, M1, M2, …). This makes the verdict table sortable and scannable at a glance.

## re-review structure

```yaml
# When to use this template:
# - Another agent wrote fixes for your review findings
# - User asked "re-review" or "verify the fixes"
# - You need one clean verdict per finding, not a full re-analysis

# Process (one turn per re-review):
# 1. Read all affected files (parallel reads)
# 2. Build finding checklist with expected fix patterns
# 3. Trace each finding through code
# 4. Run verification (imports + tests)
# 5. Deliver structured per-finding verdict
```
