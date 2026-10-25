# Claude CLI Auto-Rewire & Gate Triage Consensus (2026-10-26)

## 1. Context & Problem Statement
The 6H Farm Gate Compliance Watchdog report surfaced 4 major recurring blocks across 524 log entries:
1. `[Worker Dispatch] investigate` (40 hits): `delegate_task` denied due to missing `BUDGET: <= N calls`.
2. `[Worker Dispatch] subagent_edit_blocked` (27 hits): `delegate_task` attempted for code editing instead of `dispatch_worker.py`.
3. `[Anti-Scan Terminal] GUARD_SEARCH_FILES_ROOT` (25 hits) & `GUARD_DANGEROUS_ROOT` (11 hits): broad disk scans from root causing I/O hang and timeouts.
4. `[Anti-Scan Terminal] GUARD_DEVICE_LOCK_REQUIRED` (20 hits): ADB commands invoked without JIT device lock.
5. `[Cronjob Window] CONSOLE_WINDOW` (9 hits): Subprocess spawned on Windows without `CREATE_NO_WINDOW` (0x08000000), popping console and stealing focus.

## 2. Architectural Consensus (Claude CLI Consultation)

### Core Invariant
> Only auto-fix/auto-rewire when the transformation **does NOT alter semantics** and **does NOT escalate or alter execution permissions/tiers**.
> In all other cases, enforce **Fail-Fast** paired with a copy-pasteable `REQUIRED_ACTION_O1` block.

### Triage Matrix

| Violation Group | Safe Strategy | Implementation Pattern | Why Auto-Rewire is / isn't Allowed |
|---|---|---|---|
| **Investigate Budget** | Auto-Inject Default | Inject `BUDGET: <= 8 calls` on read-only routes with telemetry `AUTO_INJECTED_DEFAULT` | Read-only investigation has no side effects; clamping keeps it within safe call budget without human intervention. Do NOT auto-inject for write routes (write budget determines Tier). |
| **Code Edit via delegate_task** | Fail-Fast + Action Mandate | Block with pre-filled `pythonw D:/Taadaa/tools/dispatch_worker.py --workdir ... --file ... "<prompt>"` | `dispatch_worker.py` enforces a completely different execution contract (Context Pack, anchor, Tier fallback). Silent rewiring changes the executor without explicit review. |
| **CONSOLE_WINDOW** | Auto-Inject Low-Level | OR-merge `creationflags \|= 0x08000000` (`CREATE_NO_WINDOW`) in win32 subprocess runner | Purely an execution environment safety shim; zero semantic alteration. Must OR-merge (never overwrite existing caller flags like `CREATE_NEW_CONSOLE`). |
| **Root Scans (GUARD_SEARCH_FILES_ROOT)** | Fail-Fast + Action Mandate | Deny immediately with pre-filled targeted path (`D:/Taadaa/tools/<subpath>`) | Auto-narrowing path is guessing user/task scope; returns silent incomplete data and breaks Scope Lock. |
| **Missing Device Lock** | Fail-Fast + Action Mandate | Deny with copy-pasteable JIT lock wrapper command | Lock ownership strictly belongs to `host + pid + lock_id`. Auto-acquiring masks concurrency contention. |

## 3. Storage Hierarchy: Rules vs Dynamic Skills

- **`rules.json` (GuardGate):**
  - Binary pass/fail decisions detectable via AST / regex / static parameters.
  - High blast radius (I/O hang, hardware corruption, account compromise).
  - Evaluated at tool invocation (Step 0 pre-tool interception).
- **Dynamic Skills (`record_skill_knowledge.py`):**
  - Contextual knowledge: Tier selection, Context Pack construction, why budgets exist.
  - Injected into prompt before tool execution to prevent bad actions from being conceived.
- **Rule-Migration Threshold:**
  - When a rule in Dynamic Skills still produces repeated denials (e.g. 40 investigate blocks, 27 edit blocks), the skill guidance has suffered attention decay.
  - Action: Promote the requirement to a mechanical pre-tool gate with pre-filled `REQUIRED_ACTION_O1`.

## 4. Anti-Patterns to Prevent
1. **Silent Rewriting:** Never fix an agent's intent in secret. Always surface `AUTO_INJECTED_DEFAULT` so the agent's context and metrics reflect the transformation.
2. **Deny Loop:** Never design a gate that denies without copy-pasteable remediation.
3. **Flaky Path Normalization:** Always normalize Windows paths (`os.path.normpath`, lowercase drive letter) before matching guard rules (`D:/Taadaa` vs `d:\taadaa\`).
4. **Heredoc Shell Traps:** Multiline heredocs (`cat << 'EOF'`) in bash/MSYS on Windows break into separate lines and get rejected by terminal command allowlists. Always write prompts to a `.txt` file first, then redirect via `< prompt.txt`.
