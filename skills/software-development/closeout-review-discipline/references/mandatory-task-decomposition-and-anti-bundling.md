# Mandatory Task Decomposition and Anti-Bundling Discipline

## 1. Context & Incident Analysis (The Bundling Trap)

In multi-module incident remediation (such as phone farm feed session, watchdog, and follow recovery), coordinators frequently fall into the **Task Bundling Trap**:
- **Cognitive Failure 1: "Lười chốt phiên nhiều lần" (Closeout Evasion):** The coordinator perceives running `closeout_gate.py` as an expensive gate loop. To "save time", it bunches 3–4 distinct bug fixes into a single turn/dispatch.
- **Cognitive Failure 2: "Semantic Conflation":** The coordinator rationalizes that because all fixes relate to "the feed session", they belong in one task.
- **Cognitive Failure 3: Skipping Gate 1 (Decomposition):** Checklist item 1 of Gate 5 is answered affirmatively without verifying isolation.

### The Concrete Consequence: Reviewer Fallback & Remediation Quagmire
- Bundling 3 fixes across 6 files generated +566 / -64 lines, totaling ~40,087 bytes (>40 KB) diff.
- Sol Web (`model: "review"`) has a strict 37 KB Cloudflare payload ceiling and a 24,000-byte safe diff ceiling (`SOL_WEB_DIFF_FALLBACK_BYTES = 24_000`).
- When diff > 24 KB, `closeout_gate.py` triggers an **automatic fallback to Terra Codex (`cx/gpt-5.6-terra-high`)** for full un-truncated review.
- While Terra Codex bypasses payload limits up to 4 MiB, its massive context enables exhaustive cross-module analysis. It scrutinizes edge cases across all 6 files (XML fallback, OCR leakage, streak date arithmetic, telemetry math, dead branches), dragging the session through 4+ remediation rounds (74 → 77 → 78 → 81 → 85+).

## 2. Hard Invariants for Task Decomposition (Gate 1 Enforcement)

Before creating or dispatching any code-surgery task, the coordinator MUST enforce the **1-Concern Blast Radius Ceiling**:

1. **Strict 1-Concern Limit:**
   - Every task MUST address exactly **one semantic defect** or feature.
   - Example of violation: Fixing follow cooldown logic AND watchdog empty-cluster parsing AND swipe smoke XML retry in one dispatch.
   - Correct pattern: 
     * Task A: Follow cooldown logic (`multi_machine_feed_session.py`, `feed_swipe_smoke.py`) -> Closeout Gate A.
     * Task B: Watchdog JSON parsing (`feed_session_watchdog.py`) -> Closeout Gate B.
     * Task C: XML retry filtering -> Closeout Gate C.

2. **Hard Blast Radius Budget:**
   - **Production files:** $\le$ 2 files modified (excluding dedicated test files).
   - **Total numstat:** $\le$ 150 lines diff (additions + deletions).
   - **Diff byte estimate:** $\le$ 18,000 bytes. This guarantees 100% diff auditability under Sol Web without triggering truncation or Terra Codex fallback.

3. **Sequential Execution Contract:**
   - Multi-issue requests MUST be split into a sequential pipeline: `Task 1 -> Focused Test -> Scoped Closeout -> Commit/Push -> Task 2 -> ...`.
   - Never combine tasks to avoid running the gate. Running three 5-minute single-file gates is 10x faster and more reliable than running one 40-minute 6-file remediation nightmare.

4. **Fail-Fast Worker Contract:**
   - Worker dispatch prompts MUST declare:
     ```text
     CONCERN_ID: <single_concern_name>
     ALLOWED_FILES: [<file1>, <file2>]
     MAX_LINES: 150
     ```
   - If the worker determines in its first 3 iterations that fixing the issue requires modifying >2 production files or crossing module boundaries, it MUST abort and return proposed sub-contracts to the Coordinator.
