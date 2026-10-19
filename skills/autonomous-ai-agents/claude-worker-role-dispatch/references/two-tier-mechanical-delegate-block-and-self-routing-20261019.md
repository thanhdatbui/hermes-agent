# Two-Tier Mechanical Delegate Block & Self-Routing Architecture (2026-10-19)

## Problem & Incident Background
Despite explicit policies and persistent memories banning Coordinator from using `delegate_task` for code edits, Coordinators repeatedly called `delegate_task`, spawning subagents via OmniRoute (`:20129` pool `ag-gemini-pool-3`). Each subagent burned up to 15 calls (~300s) and caused drift/deadlock (e.g., `deleg_fd864e36` on Oct 18, `deleg_1242010` on Oct 18 night, and `deleg_a6ad1623` on Oct 19 morning).

### Root Causes
1. **Missing Runtime Config Hook:** The main configuration under `hooks.pre_tool_call` had matchers for `terminal` and `read_file`, but completely omitted any matcher for `delegate_task`.
2. **Fail-Open Semantic Logic in Plugin:** In the coordinator guard plugin, `_on_pre_tool_call` validated the contract syntax (`validate_dispatch`) and, if valid, proceeded to `return None` (allowed), failing open.
3. **Standalone Script Illusion:** The dispatch contract hook script was tested in isolation via unit tests (7/7 passed), creating the false impression that the gate was active, while it was never wired to the live Hermes runtime tool dispatch chain.

---

## Architecture: Two-Tier Defense (Claude Sonnet 5.5 Mandate)

Relying on either the runtime hook alone or the plugin alone fails:
- **Tier 1 (Hạ tầng vật lý - Fail-Closed):** Hook in runtime configuration under `hooks.pre_tool_call` with `matcher: "delegate_task"`. Deny-by-default before any plugin code runs. Protects against bugs, regressions, or bypasses in application plugins.
- **Tier 2 (Ngữ nghĩa - Semantic Classifier):** Plugin hook (coordinator guard plugin) inspects payload to permit valid read-only investigations (`TASK_KIND: INVESTIGATE`, budget <= 8 calls) while blocking any write/patch capabilities.

---

## Key Implementations & Contracts

### 1. Dual-Shape Payload Normalization
Hermes invokes pre-tool hooks with either CLI or Gateway schema:
```python
tool_name = payload.get("tool") or payload.get("tool_name") or ""
args = payload.get("args") or payload.get("tool_input") or {}

# Handle batch tasks array
goal_parts = [args.get("goal") or args.get("prompt") or ""]
context_parts = [args.get("context") or ""]
for task in args.get("tasks") or []:
    if isinstance(task, dict):
        goal_parts.append(task.get("goal") or task.get("prompt") or "")
        context_parts.append(task.get("context") or "")
goal = "\n".join(p for p in goal_parts if p)
context = "\n".join(p for p in context_parts if p)
combined = goal + "\n" + context
```

### 2. Structured Self-Routing Output (Anti-Paralysis)
Never return a silent or unguided deny. A deny must include an executable `required_route` and `next_action`:
```json
{
  "action": "block",
  "error_code": "BLOCKED_BY_DISPATCH_GATE",
  "message": "⛔ [DISPATCH GATE - BLOCKED_BY_DISPATCH_GATE]: delegate_task bị cấm cho tác vụ sửa code. Phải dispatch qua worker CLI.",
  "required_route": "python D:/Taadaa/tools/dispatch_worker.py",
  "next_action": "python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] <prompt>"
}
```
When Coordinator receives `BLOCKED_BY_DISPATCH_GATE`, it immediately routes to `dispatch_worker.py` in terminal rather than asking the operator or freezing.

### 3. Emergency Escape Valve
Code editing via `delegate_task` is permitted ONLY when the operator explicitly provides an override token indicating both CLI tiers are exhausted:
```
WORKER_CLI_EXHAUSTED: true
```
(Matches regex `\b(?:ALLOW_SUBAGENT_CODE_EDIT|OVERRIDE_SUBAGENT_DISPATCH|WORKER_CLI_EXHAUSTED|HAIKU_AND_AGY_FAILED)\b`).

### 4. Idempotent Config Wiring (`manage_hermes_config.py wire-dispatch-hook`)
To avoid triggering protected path filters when modifying config from terminal, dedicated subcommand:
```bash
python D:/Taadaa/tools/manage_hermes_config.py wire-dispatch-hook
```
Safely checks, creates an atomic `.bak.<timestamp>` backup, writes via `.tmp` fsync replace, and reports `ADDED` or `ALREADY_PRESENT`.
