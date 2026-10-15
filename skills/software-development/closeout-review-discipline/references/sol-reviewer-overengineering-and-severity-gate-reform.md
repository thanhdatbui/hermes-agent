# Sol Reviewer Over-Engineering Trap & Severity-Based Gate Reform

> **Context:** Incident on 16/10/2026 where Closeout Gate (Sol High :20129) ran for 27 consecutive cycles (from 00:00 to 06:00, ~5 hours) chasing the >= 85 score threshold, trapped at 82–84 points over minor non-functional nitpicks.

---

## 1. Root Cause Analysis: The 85-Score Stochastic Trap

### A. Goodhart's Law & LLM Numerical Score Noise
- LLM scoring (0–100) has an inherent stochastic variance of ±3–5 points on identical diffs.
- Setting a hard binary pass/fail gate at `Score >= 85` places the gate threshold directly inside the noise margin between 82 and 86.
- The coordinator ends up "playing the lottery" across 20+ cycles rather than performing genuine safety engineering.

### B. The Micro-Optimization Spiral (Code & Test Churn)
To squeeze 2-3 extra points out of Sol High, the agent was forced into:
1. **Diff Budget Trimming:** Shaving bytes to stay strictly under the 21.299 KB L0 budget of `sol_payload_guard.py` (deleting error messages, shortening variable names).
2. **Feature Creep via Nitpicks:** Adding execution latency telemetry (`duration_ms`), building complex in-memory cache TTL and locks (`_CACHE_LOCK`, `_invalidate_cache()`) for a script executed via cron once per minute.
3. **Reviewer Penalty Feedback Loop:** Adding the cache introduced new review surfaces (TOCTOU race in cache, lock scope deadlock concerns, global mutable state), which caused the reviewer to deduct MORE points for architectural complexity.

---

## 2. Claude CLI Architectural Verdict

When consulted by Operator to evaluate whether to keep Sol High and whether the workflow was over-engineered:

1. **Keep Sol High as Independent Reviewer:**
   - **Cross-Family Review Value:** Sol High (GPT-4o via OmniRoute `:20129`) is free, consumes zero Claude quota, and catches genuine blind spots that Gemini/Claude workers miss.
2. **Abolish Rigid Numerical Gate (`Score >= 85`):**
   - The numerical score gate is the direct cause of over-engineering and 5-hour session stalls.
3. **Transition to Severity-Based Gate (`BLOCKER == 0`):**
   - **BLOCKER:** Direct farm safety violation, uncapped loops, unhandled destructive operations, ADB port collisions. Must be resolved before merge.
   - **MAJOR:** Logic edge case or performance risk. Address or explicitly document justification.
   - **NIT:** Formatting, style, telemetry formatting, optional metrics. Ignored for gate pass/fail.

---

## 3. Recommended Remediation & Safeguards

### A. Hard Cap on Remediation Rounds
- Maximum 2 review rounds per task.
- If no BLOCKER remains after Round 2, the change MUST be approved for merge.
- If blocked after Round 2, immediately hand off to Operator or Claude CLI with specific BLOCKER findings rather than looping endlessly.

### B. Separation of Mechanical Checks from LLM Judgment
- Diff size, lint, and test pass/fail must be enforced by deterministic local scripts (pytest, git diff --numstat), NOT by asking an LLM to deduct subjective points.
- Sol High should exclusively assess: (1) Farm Safety & Device Isolation, (2) Core Business Logic Correctness.

### C. Anti-Overengineering Rule for One-Shot Watchdogs
- Do not add multi-threaded in-memory caching, TTL expirations, or complex state machines to simple periodic cron scripts unless explicitly required by high invocation frequency (> 10 Hz).
- Simplicity (read directly, execute atomically, fail closed) is superior to complex stateful caching.
