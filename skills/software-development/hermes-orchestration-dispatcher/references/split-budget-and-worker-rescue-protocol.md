# Split-Budget and Worker Rescue Protocol (Anti-Malicious Compliance & Anti-Freeze)

**Context:** Sol Web (`gpt-web-sol`) Round 2 Certified Architecture Review (2026-10-02).
**Problem:** Coordinator was freezing tasks into `L3 BLOCKED` by counting test verification lines into the <= 30 lines production code budget, and refusing to takeover when a worker timed out on tests despite successfully patching logic.

---

## 1. Root Cause: Safety Theater & Malicious Compliance

When autonomous coordinators operate under rigid numerical guardrails, they frequently fall into the **Malicious Compliance Pattern**:
- Treating formal line counts as a proxy for semantic risk (`diff size = risk`).
- 14 lines of state machine logic + 42 lines of test assert updates was treated as "56 lines > 30 lines -> DANGEROUS".
- In reality, test assertion updates are **Verification Alignment**, having zero runtime blast radius.
- The coordinator used the procedural rule to dodge responsibility and push a `BLOCKED` status to the user.

---

## 2. Invariant 1: Split-Budget Architecture (Production vs Verification)

### Production Code Logic Budget
- **T1 (Minor Field Tweak):** Exactly 1 file, <= 15 cumulative diff lines.
- **L2 (Controlled Recovery Mode):** Max 2 files, <= 30 cumulative diff lines.
- Strictly enforced: No refactoring, no renaming, no extra dependencies.

### Verification Alignment Budget
- Files matching `is_test_file(path)` (`tests/**`, `test_*.py`, `conftest.py`):
- Granted a dedicated budget of **<= 120 diff lines**.
- **PROHIBITED:** Aggregating test verification lines into the production code budget to justify declaring `BLOCKED`.

---

## 3. Invariant 2: Worker Timeout Rescue Protocol

When a Worker subagent times out or encounters a transient API failure:
1. **Analyze Checkpoint:** Inspect `git status --porcelain` and `git diff`.
2. **Classify Dirty State:**
   - **Trusted Dirty:** Changes made by the worker of the *current task* within the declared scope lock, where logic is intact and valid.
   - **Foreign Dirty:** Unrelated files modified outside the task's scope lock.
   - **Unknown Dirty:** Unattributable dirty state.
3. **Execution Protocol:**
   - If **Trusted Dirty** (logic patched 90%, timed out during test run/assert update): Coordinator **MUST TAKE OVER** under L2 Controlled Recovery Mode to finish the remaining test assertions and run verification.
   - It is a **CRITICAL INFRACTION** to declare `L3 BLOCKED` when the exact diff and root cause are already known.

---

## 4. Hard Hook Gate Protections (`farm-coordinator-guard` / `farm_policy.py`)

To prevent bypass while enabling legitimate verification alignment, the hook gate enforces:

1. **Centralized Test Classifier (`is_test_file`):**
   - Single Source of Truth shared between Gate 2 (`validate_dispatch`) and Gate L2 (`coordinator_write_gate`).
   - Anti-Spoofing: Rejects files disguised as tests inside production source trees (`/src/`, `/app/`, `/lib/`, `/core/`, `/flows/`, `/services/`, `/controllers/`).
2. **L2 Reason Binding (`is_related_test_file`):**
   - Test files modified under L2 must share stem naming (`follow_state` <-> `test_follow_state`) or repository boundaries with the failed target.
   - Unrelated test files are blocked (`L2 TEST UNBOUND`).
3. **Ledger Backward Compatibility:**
   - Older sessions automatically migrate `l2_biz_lines = l2_lines` and `l2_test_lines = 0`.
