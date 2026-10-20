# Zero-Waiting-State Adversarial Audit & Anti-Paralysis Protocol (2026-10-20)

## 1. Context & Incident Summary
Operator caught Coordinator violating Gate 6 (delivering text-only narrative after browser inspection) and hallucinating model names by reading stale code and hero marketing banners.
When Operator asked: *"Có gây khóc lóc blocked k? Thảo luận lại vs claude đi"*, Coordinator conducted a 2-round adversarial architectural debate with **Claude Sonnet 5.5 Planner** (`--role planner`, max 10 turns via `claude_worker.py`).

---

## 2. Flaws in Draft 1 (Identified by Operator & Coordinator)
1. **The "Operator Override Token" Trap:**
   Draft 1 proposed: *"From 2nd violation, lock dispatch gate, only unlock via operator override token"*.
   - **Flaw:** Creates an explicit `WAITING_OPERATOR` state. The Coordinator halts, whines, and asks the user to manually type an unlock token.
2. **The "Stop Hook" Missing Next-Action Trap:**
   - **Flaw:** Dropping output without an automated path to resolution forces the LLM into a cognitive loop, outputting `BLOCKED` and complaining.

---

## 3. Consensus Architecture: Separating Liveness from Safety

Claude Sonnet 5.5 established the fundamental rule:
- **Liveness:** The system process always proceeds; no waiting states (`WAITING_*`) exist in the finite state machine.
- **Safety:** Unverified claims are never elevated to Facts (`VERIFIED`), and cannot unlock non-reversible actions (`R2`).
- **What is blocked is claim promotion and R2 execution, NOT the worker process.**

---

## 4. The 4 Mechanical Pillars of Zero-Waiting-State

### A. Evidence Capsule at Tool Wrapper
Instead of hoping the LLM calls `browser_vision`, the UI tool wrapper automatically produces a structured **Evidence Capsule**:
`{evidence_id, device_id, ts, sha256, ocr_text, capture_status}`
If capture fails, `capture_status=FAILED`, and claims default to `HYPOTHESIS`.

### B. Default-Deny & Taint Propagation
- Free-form text output from LLM is structurally tagged as `[HYPOTHESIS]`.
- `HYPOTHESIS` cannot serve as a precondition for destructive/irreversible actions (`R2`).
- A task completing with only hypotheses ends in `DEGRADED`, never `PASSED`.

### C. Runner-Executed Verification Loop (Max N=3)
- Verification actions (opening dropdowns, cropping OCR) are executed deterministically by the harness runner, not suggested as advice to the LLM.
- Budget: Max N=3 attempts. If verification fails, the FSM transitions directly to `DEGRADED` or `ABORTED_SAFE`, releases resources, and immediately pulls the next task from the queue.

### D. 100% Elimination of WAITING_OPERATOR
- The state machine ends only in: `VERIFIED`, `DEGRADED`, or `ABORTED_SAFE`.
- Device and gate locks use **Lease-Locks with strict TTL and Heartbeat**, preventing stale locks without requiring manual human intervention.
