# Claude CLI Consensus: Auto-Wiring vs Fail-Fast Boundaries in Mechanical Gates

> Reference from 6H Watchdog remediation (Gate G3, G7, G8 violations).
> Architecture consensus approved via Claude Code CLI consultation.

## Core Principle
Only apply **Auto-Wiring (Auto-Fix/Rewrite)** when the transformation preserves exact semantic intent and DOES NOT alter permission, executor tier, or execution scope. For all other violations, **Fail-Fast immediately** accompanied by an executable, copy-pasteable `REQUIRED_ACTION_O1` block.

---

## 1. Tactical Resolution by Gate Class

| Gate / Rule | Strategy | Execution Pattern | Rationale |
| :--- | :--- | :--- | :--- |
| **`investigate` route** | Auto-Wiring (Read-Only) | Prepend `BUDGET: <= 8 calls. FAIL_FAST: ...` and mark telemetry with `AUTO_INJECTED_DEFAULT`. | Read-only investigations cannot damage state; adding a safe budget clamp keeps the workflow moving without stall. |
| **`subagent_edit_blocked`** | Fail-Fast + Action Mandate | **CẤM auto-rewire ngầm.** Deny immediately with pre-filled `dispatch_worker.py` command containing target file. | `dispatch_worker.py` uses an entirely different contract (Context Pack, anchor, model tier). Silent rewiring changes the executor without explicit authorization. |
| **`CONSOLE_WINDOW`** | Auto-Wiring (Engine-level) | In `subprocess.run`/`Popen` on Windows, bitwise OR `creationflags |= 0x08000000` (`CREATE_NO_WINDOW`). Skip if `CREATE_NEW_CONSOLE` or `DETACHED_PROCESS` is explicitly set. | Window popping is a low-level OS artifact that steals operator focus; fixing it at the runner layer has zero semantic side effects. |
| **`GUARD_SEARCH_FILES_ROOT` / `GUARD_DANGEROUS_ROOT`** | Fail-Fast + Action Mandate | **CẤM auto-narrow path.** Deny fast with `REQUIRED_ACTION_O1` pointing to exact repo subpath or `inspect_machine.py`. | Auto-narrowing guesses scope, risks false negatives without warning, and violates Scope Lock invariants. |
| **`GUARD_DEVICE_LOCK_REQUIRED`** | Fail-Fast + Action Mandate | **CẤM auto-acquire lock.** Deny fast with exact JIT-lock syntax: `python D:/Taadaa/tools/inspect_machine.py <N>`. | Lock ownership is bound strictly to `host + pid + lock_id`. Gate cannot guess lock lifetime or lease owner. |

---

## 2. Guidance Partitioning: `rules.json` vs Dynamic Skills

- **`guardgate/rules.json`:**
  - Reserved for binary violations detectable via regex or AST.
  - Used when failure consequences are severe (disk I/O hang, farm safety, USB micro-drop).
  - Intercepts synchronously at tool boundary.
- **Dynamic Skill Routing (`record_skill_knowledge.py`):**
  - Reserved for contextual architectural knowledge (Tier selection, Context Pack structuring, rationale for budget floors).
  - Injected pre-execution into agent prompts to eliminate violations before they reach the gate.
- **Promotion Rule:** When a rule in Dynamic Skills still results in repeated gate denials in the 6H rollup (e.g. `investigate` 40 times, `subagent_edit` 27 times), it must be promoted to an active gate with a deterministic template.

---

## 3. Anti-Patterns in Gate Auto-Wiring
1. **Silent mutation without telemetry:** Model never learns. Every auto-fix must increment a distinct `auto_fixed` counter in watchdog logs.
2. **Deny $\rightarrow$ Auto $\rightarrow$ Deny loop:** An auto-injected value failing downstream validator gates.
3. **Changing executor or tier under the hood:** Never substitute a cheaper/different worker secretly.
4. **Non-idempotent injection:** Re-injecting budget flags repeatedly on retries.
