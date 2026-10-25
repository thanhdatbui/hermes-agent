# Cowboy Coordinator Boundary, Idle Evaluation Bias & Zero-Block Invariants

## 1. Cowboy Coordinator Boundary (Gate 3 & Gate 6 Violation)
- **Problem:** Coordinator directly applying patches via `patch` or `write_file` in the primary session without dispatching a Worker subagent.
- **Invariants Violated:**
  - **Gate 3 (Worker Dispatch & Role Separation):** The Coordinator's role is strictly limited to Read, Plan, Dispatch, and Verify. All implementation/code write actions MUST be executed through a pinned Worker via `python D:/Taadaa/tools/dispatch_worker.py` (Tier 1: Sol -> Tier 2: Agy -> Tier 3: Haiku).
  - **Gate 6 (Self-Report = 0 Evidence):** A Coordinator that writes its own code and runs its own tests produces self-attested claims lacking independent external verification.
  - **L2 Emergency Surgery Bounds:** L2 allows direct Coordinator modification ONLY after 2x Transient retries fail or 2x Structural failures, strictly capped at $\le 2$ files and $\le 30$ lines total diff (`git diff --numstat`). Modifying 50+ lines directly without prior dispatch is a critical discipline breach.

## 2. Idle-Window Evaluation Bias (Chống Ngụy Biện Khung Giờ Ngủ Đông)
- **Anti-Pattern:** Looking at 0 errors in the last 1–4 hours and concluding a hook or system is "100% stable / self-healed", ignoring the fact that the user was inactive and few chat commands were executed.
- **Rule:** Hook and gate violation rates MUST be evaluated against:
  1. All-time cumulative error counts.
  2. Active interactive session windows (when user messages and coordinator actions were actively occurring).
  3. Error rate normalized per user prompt / per tool call.
  - Low raw error count during an idle period is a false positive of stability.

## 3. Zero Passive Hard-Blocks (Action Mandate Hierarchy)
- **Principle:** Every gate failure must maintain momentum. A passive hard-block that exits non-zero without a next step causes apologetic loops and cognitive paralysis.
- **Action Hierarchy:**
  1. **REWRITE (Auto-Rewire):** Hook automatically transforms and reroutes the invocation to a safe canonical target (e.g., `delegate_task` with code edits rewired to `dispatch_worker.py` with `[AUTO-REWIRED]` header).
  2. **MANDATE (Action Mandate O(1)):** When auto-rewire cannot safely guess intent, emit a structured block with `REQUIRED_ACTION_O1.command` providing a copy-pasteable executable alternative that narrows scope.
  3. **PIVOT (Queue Continuity):** If a specific resource (device or account) is locked in a primary shift, fungible batch jobs automatically pivot to the next idle item in the farm queue. Targeted incidents enter `WAIT_FOR_LOCK` while the coordinator proceeds to other independent queue tasks.

## 4. Closeout Gate Sanctuary
- **Invariant:** `closeout_gate.py` has proven stability with autonomous Sol Repair remediation (3–7 minute cycle). It is an invariant sanctuary: strictly forbidden from arbitrary modification, scope expansion, or unsolicited rewrites.
