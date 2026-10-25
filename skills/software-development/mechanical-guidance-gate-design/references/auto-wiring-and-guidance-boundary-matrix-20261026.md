# Auto-Wiring & Guidance Injection Boundary Matrix (2026-10-26)

## 1. Core Principle (Claude CLI Architecture Consensus)
Only auto-fix (Auto-Rewire) when the transformation is meaning-preserving, permission-neutral, and deterministic. In all other cases, fail-fast with a machine-readable, copy-pasteable `REQUIRED_ACTION_O1` block. Never leave the agent in a cognitive void.

## 2. Decision Matrix by Gate Class

| Gate / Rule | Strategy | Mechanism | Rationale & Safety Boundary |
|:---|:---|:---|:---|
| **Investigate Route (`BUDGET`)** | **Auto-Rewire (Read-Only)** | Auto-inject `BUDGET: <= 8 calls` with `AUTO_INJECTED_DEFAULT` marker | Prevents cognitive void loops; ONLY safe for read-only routes. For write/edit routes, budget represents Tier escalation and must be explicitly approved. |
| **Code-Edit via `delegate_task`** | **Fail-Fast + O(1) Pivot** | DENY with pre-filled `dispatch_worker.py --workdir ... --file ...` command | `dispatch_worker.py` uses a different contract (Context Pack, anchor, Tier). Secretly switching executors violates permission transparency. |
| **Console Window (`CONSOLE_WINDOW`)** | **Auto-Rewire (Subprocess)** | OR-merge `creationflags \|= 0x08000000` (`CREATE_NO_WINDOW`) on Windows | Invisible execution is strictly safer on headless farm workers. Must OR-merge (never overwrite) and skip if caller explicitly requested `CREATE_NEW_CONSOLE`. |
| **Root/Dangerous Scans (`GUARD_SEARCH_FILES_ROOT`)** | **Fail-Fast + Narrow Path** | DENY with pre-filled repo allowlist or targeted machine log path | Auto-narrowing guesses user scope, risks silently returning false/partial data, and breaks Scope Lock. |
| **Farm Device Lock (`GUARD_DEVICE_LOCK_REQUIRED`)** | **Fail-Fast + JIT Lock Template** | DENY with exact `python D:/Taadaa/tools/inspect_machine.py <N>` command | Locks belong strictly to `host+pid+lock_id`. Auto-acquiring locks creates phantom locks and race conditions across 40+ parallel farm devices. |

## 3. Storage Hierarchy: `rules.json` vs Dynamic Skills

- **`rules.json` (GuardGate Invariants):**
  - Reserved for binary violations detectable via regex or AST.
  - Hard stops with catastrophic failure modes (I/O deadlock, USB micro-drop, device bricking).
  - Evaluated pre-tool call.

- **Dynamic Skill Routing (`record_skill_knowledge.py`):**
  - Reserved for contextual rationale: why budget is needed, Tier selection logic, Context Pack templates.
  - Injected into prompt at Turn 1 via `skill_injector.py` to prevent violations before they occur.
  - **Promotion Rule:** If a skill is loaded and injected, yet the agent triggers the same DENY rule $\ge 3$ times across sessions (e.g. 40 investigate blocks), promote that rule to a mechanical gate with pre-filled `REQUIRED_ACTION_O1`.

## 4. Anti-Patterns to Prevent
1. **Silent Magic:** Model cannot learn if errors are silently papered over. Log `auto_fixed` events to dedicated telemetry buckets in audit logs.
2. **Looping Rewrites:** Gate A auto-rewires into a format that triggers Gate B, creating an infinite ping-pong.
3. **Overwriting Flags:** Overwriting caller-specified `creationflags` or `timeout` rather than applying minimum floors/merges.
4. **Unnormalized Paths:** Path comparisons must use normalized lowercase paths (`os.path.normcase(os.path.abspath(p))`) to avoid Windows drive-letter bypasses (`D:/` vs `d:\`).
