# Claude CLI Architectural Consensus: Auto-Wiring vs Active Pivot Boundary & Anti-Paralysis Invariants (2026-10-26)

## 1. Context & The "Paralysis vs Anti-Whining" Dilemma
When compliance watchdogs report high rates of gate interceptions (e.g. `G3 Worker Dispatch Gate` 164 blocks on `subagent_edit_blocked` and 40 blocks on `investigate`; `G7 Anti-Scan Terminal Guard` 118 blocks on `GUARD_DANGEROUS_ROOT`), agents face two failure modes:
1. **Silent Veto Paralysis (Khóc lóc / Bại liệt):** Passive denial (`exit 1` with a bare error) throws the agent into a cognitive void, leading to repetitive apologetic chatter or whining for the operator to run commands manually.
2. **Reckless Auto-Rewiring (Tự tiện đổi executor/scope):** Trying to "auto-fix" everything mechanically by silently changing the executor, target file, or directory path can violate safety invariants, change authorization levels, or mask root causes.

Consultation with Claude Code CLI (2026-10-26) established the authoritative boundary between **Auto-Wiring** (transparent in-flight mutation) and **Active Pivot** (deterministic fail-fast with copy-pasteable next action).

---

## 2. The Core Decision Boundary: Auto-Wiring vs Active Pivot

> **Invariant:** An interception may ONLY be auto-wired (mutated and permitted in-flight) if the transformation is **lossless, idempotent, and preserves executor, tier, authorization, and scope boundaries**. All other cases MUST fail-fast with a pre-filled, copy-pasteable `REQUIRED_ACTION_O1` (Active Pivot).

### Matrix of Determinations

| Gate / Route | Decision | Mechanism | Rationale & Safety Guardrails |
| :--- | :--- | :--- | :--- |
| **`investigate` (Read-only)** | **Auto-Wiring** | Auto-inject `BUDGET: <= 8 calls` | Read-only inspection has fixed max budget (8). Lossless intent. Mark telemetry with `AUTO_INJECTED_DEFAULT`. **NEVER** auto-inject for write/edit tasks where budget reflects a Tier decision. |
| **`CONSOLE_WINDOW` (Subprocess)** | **Auto-Wiring** | Auto-inject `CREATE_NO_WINDOW (0x08000000)` | Windows subprocesses popping CMD windows steals user focus. Lowest-level shim: `creationflags \|= 0x08000000`. **Rule:** OR-merge flags; never overwrite. Skip if caller explicitly requested `CREATE_NEW_CONSOLE` or `DETACHED_PROCESS`. |
| **`subagent_edit_blocked`** | **Active Pivot** | Fail-fast with pre-filled `dispatch_worker.py` command | `dispatch_worker.py` has a completely different contract (Tier selection, Context Pack, anchor check, canary gate). Silently auto-rewiring an arbitrary subagent edit into a full worker changes executor & tier without explicit contract validation. Provide ready-to-run CLI string. |
| **`GUARD_SEARCH_FILES_ROOT` / `GUARD_DANGEROUS_ROOT`** | **Active Pivot** | Fail-fast with pre-filled safe target/subfolder | Auto-narrowing a path (e.g. `D:/Taadaa` -> `D:/Taadaa/tools`) guesses user intent, risks returning incomplete search results silently, and violates Scope Lock. Fail fast with pre-filled cwd or machine log subfolder. |
| **`GUARD_DEVICE_LOCK_REQUIRED`** | **Active Pivot** | Fail-fast with JIT lock template (`with_device_lock.py` or `inspect_machine.py`) | Lock ownership is cryptographically/process-bound to `host + pid + lock_id`. Auto-acquiring a lock on behalf of an un-isolated process causes lock contention, leaked locks, and race conditions. |

---

## 3. Guidance Partitioning: `rules.json` vs Dynamic Skill Routing

Where should architecture lessons be deposited to eliminate repetitive violations?

1. **GuardGate `rules.json` (via `update_guidance.py`):**
   - **When:** Violations that are strictly binary, detectable via static regex/AST, and carry severe operational penalties (disk I/O freeze, device collisions, process window stealing).
   - **Behavior:** Intercepts at execution time. Emits concise architectural rationale + copy-pasteable `REQUIRED_ACTION_O1`.
2. **Dynamic Skill Routing (`record_skill_knowledge.py`):**
   - **When:** Contextual guidance, workflow heuristics, Tier selection tradeoffs, and Context Pack formatting.
   - **Behavior:** Injected before tool invocation ($O(1)$ dynamic retrieval) to guide the agent to formulate compliant commands on Turn 1.
3. **Escalation Rule:**
   - If guidance in a dynamic skill still experiences high rejection frequency (e.g. `investigate` 40 times, `subagent_edit` 27 times), the skill is failing to govern behavior during high context load. It **MUST** be upgraded to a mechanical gate with a pre-filled CLI template.

---

## 4. Anti-Patterns in Auto-Wiring & Mechanical Gates

1. **The Silent Fix Anti-Pattern (Sửa ngầm mất dấu):**
   - Mutating tool arguments without telemetry makes the model unaware of the correction, preventing learning.
   - *Requirement:* Auto-wired events must be logged with a dedicated flag (`auto_fixed: true`, `AUTO_INJECTED_DEFAULT`) and aggregated as `REWIRED` in compliance watchdogs, distinct from raw `PASS` and `FAIL`.
2. **Deny-Auto-Deny Loops:**
   - Auto-rewriting arguments into a shape that triggers a downstream gate (e.g., rewriting `python` to `pythonw` with a syntax error that trips a console parser).
3. **Executor / Tier Hijacking:**
   - Changing the underlying LLM provider or execution harness under the guise of an argument rewrite.
4. **Non-Idempotent Injection:**
   - Appending flags or strings repeatedly on successive passes (e.g., appending `BUDGET: <= 8 calls` multiple times).
5. **Path Normalization Bypass:**
   - Gates checking `D:/Taadaa` failing to match `d:\taadaa` or `D:/Taadaa/` due to unnormalized path comparisons. Always compare using `os.path.normcase(os.path.normpath(p))`.
6. **Test Artifact Pollution in Compliance Telemetry:**
   - Unit test suites (e.g. testing gate rejection behavior) dump synthetic violation payloads into shared production audit logs (`dispatch_audit.jsonl`, `guard_scan_audit.jsonl`).
   - Up to 70% of reported 6h compliance failures can be synthetic test runs. Compliance watchdogs MUST maintain an aggressive test exclusion filter matching known test payload signatures (`Review then apply constant change`, `grep -rn foo`, `target.py`, `pytest`).
