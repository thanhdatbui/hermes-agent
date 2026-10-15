# Closeout Gate Reviewer Rubric & Telemetry Deduplication Invariants

## Context & Incident Analysis (15/10/2026)

During closeout of the TikTok watchdog buffer window and reconcile refactoring, multiple review iterations with Sol Auditor (`closeout_gate.py` via OmniRoute `:20129`) revealed subtle review traps that degraded scores from 82 down to 38-52:

1. **The Test-Only Diff Trap:** A candidate commit containing only test cases (`tests/test_feed_session_watchdog.py`) with zero production diff was heavily penalized (score 38/100). The reviewer noted: *"Diff chỉ chứa thay đổi trong file test — không có bất kỳ thay đổi nào trong mã nguồn production... không đủ cơ sở để đánh giá logic correctness."*
2. **Duplicate Telemetry Logging:** Logging both on `was_capped` and on `minutes != 0` without mutual exclusion caused duplicate log lines on boundary events, flagged as a basic code review failure.
3. **Subsecond Timestamp Capping:** In SQLite where strings are formatted `%Y-%m-%d %H:%M:%S`, using `microsecond=999999` and then replacing with `microsecond=0` caused subtle edge case discrepancies during date comparison.

---

## 1. Sol Auditor Scoring Rubric Invariants

Sol Auditor evaluates candidate diffs against a strict 100-point rubric:
- **Logic Correctness (35 pts):** Requires genuine production changes that solve the stated issue. Commits containing ONLY test changes will fail logic correctness (< 20/35) because there is no proof of production bug remediation in the evaluated commit.
- **Test Evidence (25 pts):** Focused tests must pass, and must test actual business logic, boundaries, and failure paths — not just assert stdlib behavior.
- **Telemetry & Observability (15 pts):** Structured logs (e.g. `[RECONCILE_BUFFER_TELEMETRY]`) and thread-safe counters are rewarded; duplicate or spammy logs are penalized.
- **Farm Safety & Anti-Regression (15 pts):** Safeguards against reversing time windows, date underflow, or breaking active farm runners.
- **Code Architecture (10 pts):** Line budget compliance (e.g. <= 1450 lines), DRY adherence, clean imports, and explicit documentation of dual-copy parity.

**Golden Rule:** Always present production fixes and their companion tests together in the candidate diff against `origin/master`. If production fixes were previously committed in intermediate commits, squash them into a cohesive candidate commit before triggering closeout review.

---

## 2. Telemetry Logging Deduplication Pattern

When instrumentation captures boundary capping or status events:

### Bad Pattern (Duplicate Log on Boundary):
```python
if was_capped:
    logger.info("[RECONCILE_BUFFER_TELEMETRY] capped boundary iso=%s -> %s (minutes=%d)", iso_val, res, minutes)
if minutes != 0:  # BUG: fires a SECOND log line when was_capped is True!
    logger.info("[RECONCILE_BUFFER_TELEMETRY] iso=%s -> %s (minutes=%d, capped=%s)", iso_val, res, minutes, was_capped)
```

### Correct Pattern (Mutually Exclusive Clean Logs):
```python
if was_capped:
    logger.info("[RECONCILE_BUFFER_TELEMETRY] capped boundary iso=%s -> %s (minutes=%d)", iso_val, res, minutes)
elif minutes != 0:
    logger.info("[RECONCILE_BUFFER_TELEMETRY] iso=%s -> %s (minutes=%d, capped=False)", iso_val, res, minutes)
```

---

## 3. Subsecond Normalization for SQLite Timestamps

In farm automation databases (SQLite), timestamps are stored as ISO strings without microseconds (`%Y-%m-%d %H:%M:%S`):
- **Never do:**
  ```python
  end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
  if buffered_dt > end_of_day:
      buffered_dt = end_of_day.replace(microsecond=0)
  ```
  This creates an edge-case zone between `.000000` and `.999999` where `buffered_dt` exceeds `23:59:59.000000` but does not trigger the cap.
- **Always do:**
  ```python
  end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)
  start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
  if minutes > 0 and buffered_dt > end_of_day:
      buffered_dt = end_of_day
      was_capped = True
  elif minutes < 0 and buffered_dt < start_of_day:
      buffered_dt = start_of_day
      was_capped = True
  ```

---

## 4. Strike 3 Hand-Off Protocol Execution

When 4 consecutive closeout review rejections occur (`[REVIEWER_HANDOFF_TRIGGERED]`):
1. **Halt Immediate Coordinator / Worker Iterations:** Do not retry with the same prompt or guess further.
2. **Invoke Reviewer Self-Remediation:** Dispatch via `D:/Taadaa/tools/claude_worker.py --role worker` strictly scoped to the target files.
3. **Quota Gate Fallback:** If Claude CLI quota is stale (`stale_quota` > 2h), `claude_worker.py` automatically falls back to `ag_cli.py fix` (Antigravity Pro pool). This preserves rate limits while producing clean O(1) patches that respect line budgets and test suites.
