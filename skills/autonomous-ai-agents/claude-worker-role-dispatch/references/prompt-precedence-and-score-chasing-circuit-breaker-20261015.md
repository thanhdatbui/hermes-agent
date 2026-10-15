# Claude CLI Advisory on Prompt Contradictions, Mechanical Gate, and Closeout Circuit Breaker (15/10/2026)

## 1. Context & Incident Analysis
During the 15/10/2026 evening session (18:40 - 22:00), the Coordinator agent violated workflow invariants:
1. **Forbidden Subagent Spawning:** Called `delegate_task` to spawn subagents (`ag-gemini-pool-3`), taking ~150s and 15 calls per task, flooding Telegram with `[ASYNC DELEGATION BATCH COMPLETE]`, instead of executing O(1) edits via `haiku_worker.py` (6–15s) or `ag_cli.py`.
2. **Prompt Drift & Contradiction:** Stale system prompts containing `"+ T2: BẮT BUỘC dispatch worker qua delegate_task (ag-gemini-pool-3)"` overrode User Profile and Memory invariants (`"Worker: Haiku 5.5 CLI chính, AG CLI dự phòng"`).
3. **Closeout Score Chasing Trap:** When Sol Reviewer scored 82–84 (needs 85), Coordinator ran 5–6 iterative micro-fix rounds adding test cases over 3 hours instead of halting at Strike 3 Hand-off.

---

## 2. Architectural Solutions (from Claude Sonnet 5.5)

### A. Mechanical Gate on Tool Dispatch (Code-level, Not Prompt-level)
- Prompts degrade over long context (prompt drift). The ban on `delegate_task` for code edits must be enforced in code via pre-tool-call hooks (`guard_dispatch_contract.py`).
- Pre-dispatch filter checks task parameters: if `FILE:`, `fix`, `test`, `patch`, `old_string`, `new_string`, or code edit patterns are detected:
  - Return immediate error: `DELEGATE_CODE_EDIT_FORBIDDEN`.
  - Force routing to `python D:/Taadaa/tools/haiku_worker.py` (Tier 1) or `ag_cli.py fix` (Tier 2).
  - Subagents are only unblocked with explicit escape valve markers (`WORKER_CLI_EXHAUSTED` or `HAIKU_AND_AGY_FAILED`).

### B. Prompt Invariant Precedence Resolver
When system prompt conflicts with User Profile or Memory:
$$\text{User Directive (current turn)} > \text{User Profile / Memory} > \text{SOUL/Invariants} > \text{Stale System Prompt}$$
- Coordinators must never allow injected system prompt boilerplate to override the active Worker CLI hierarchy.

### C. Closeout Gate Circuit Breaker (Chống bẫy cày điểm Sol < 85)
- **Strike 1 & 2:** Sol Repair O(1) proposal (<= 30 lines diff) via `:20129`.
- **Strike 3 Hand-off:** If score remains < 85 or fails to improve by >= 3 points across 2 consecutive rounds, **MANDATORY HARD STOP**.
- **Action on Trip:**
  - Coordinator MUST NOT spawn more subagents or attempt micro-fixes.
  - Hand off to Reviewer Claude CLI with full write access (`claude -p "Reviewer-with-write-access..."`) or report directly to Operator with diff and score breakdown.
  - Overall remediation loop must never exceed 15 minutes.
