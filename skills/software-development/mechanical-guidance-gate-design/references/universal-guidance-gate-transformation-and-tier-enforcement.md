# Universal Guidance Gate Transformation & Mechanical Tier Enforcement

## Context & Problem Statement
In previous sessions, agent paralysis and bureaucratic loops occurred due to two architectural anti-patterns:
1. **Silent Veto Gates:** Hooks blocked unauthorized or dangerous actions (`[CONSOLE_WINDOW_BLOCKED]`, `[GUARD_FOREGROUND_TIMEOUT_EXCEEDED]`, `[HARD GATE]`) by printing plain-text error messages and exiting with status 0 or 1 without providing structured machine-readable guidance. This placed LLM coordinators in a "cognitive void", triggering iterative guessing, whining, and eventual delegation avoidance or bogus `BLOCKED` states.
2. **Terminal Backdoor Bypass:** While high-level tools like `delegate_task` were gated by `guard_dispatch_contract.py` to enforce Tier 1 (`sol_worker.py` :20129, 100% Free) -> Tier 2 (`ag_cli.py`) -> Tier 3 (`claude_worker.py`), the Coordinator could bypass the tier system entirely by invoking `python D:/Taadaa/tools/claude_worker.py --role worker` directly from the `terminal` tool, burning expensive Claude quota on routine edits.

## Implemented Mechanical Solutions

### 1. Hardened Mechanical Tier Enforcement (Fail-Closed Exit 126)
- **File:** `D:/Taadaa/tools/claude_worker.py`
- **Mechanism:** For `--role worker`, `claude_worker.py` strictly verifies provenance:
  - Requires either `--from-dispatch` CLI flag OR `DISPATCH_TIER_CALLER == "dispatch_worker"` environment variable.
  - If neither is present, it immediately logs `{"event": "mechanical_tier_gate_violation", "role": "worker"}`, prints an $O(1)$ escape command to `dispatch_worker.py`, and exits with return code `126`.
- **Caller:** `dispatch_worker.py` injects `--from-dispatch` into `haiku_cmd` when falling back to Tier 3.

### 2. Universal Action Mandate & Guidance Schema
Every pre-tool hook and guard MUST return a JSON payload with the following mandatory fields:
```json
{
  "action": "block",
  "rule_id": "<RULE_ID>",
  "message": "[<RULE_ID>] <reason>\nHƯỚNG DẪN: <guidance>\nCHỈ DẪN: <instruction>",
  "guidance": "<architectural rationale explaining WHY the action is blocked>",
  "required_action": {
    "command": "<concrete_runnable_command_or_empty>",
    "instruction": "<exact_step_to_take>",
    "description": "<summary_of_action>"
  },
  "tool": "<tool_name>",
  "timestamp": "<UTC_ISO_8601>"
}
```

### 3. All 8 Runtime Hooks Standardized
1. `guard_cronjob_safety.py`:
   - Emits structured guidance for console hiding (`pythonw`, `powershell -WindowStyle Hidden`, `creationflags=CREATE_NO_WINDOW`), script path resolution, and farm contract parameters (`touches_device`, `device_lock`, `rolling`, `max_workers`).
   - Protects against Windows `cp1252` encoding crashes via `sys.stdout.reconfigure(encoding="utf-8")`.
2. `hooks/guard_broad_grep.py`:
   - Maps all 10 scan and timeout rule IDs (`GUARD_DANGEROUS_ROOT`, `GUARD_RECURSIVE_GREP`, `GUARD_RECURSIVE_RG`, `GUARD_PYTHON_WALKER`, `GUARD_POWERSHELL_SCAN`, `GUARD_FIND_SCAN`, `GUARD_FOREGROUND_TIMEOUT_MISSING`, `GUARD_FOREGROUND_TIMEOUT_INVALID`, `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`, `GUARD_SEARCH_FILES_ROOT`) to actionable guidance and instructions.
3. `hooks/guard_read_file_size.py`:
   - Explains context window exhaustion for files > 10MB and provides immediate slice command `tail -n 200 <path>`.
4. `hooks/guard_pytest_scope.py`:
   - Explains > 900s suite timeout hazard and provides focused test command `python -m pytest <path/to/test.py> -q`.
5. `hooks/guard_model_drift.py`:
   - Explains the requirement for Sol-High pool (:20129) reviewer and provides canonical `closeout_gate.py` command.
6. `hooks/guard_closeout_discipline.py`:
   - Blocks panic rollback, unapproved push, and clarify evasion during hand-off with explicit remedial guidance.
7. `hooks/guard_device_bulkhead.py`:
   - Covers 6 blocking points: manual ADB taps, device lock requirements, ambiguous ADB device targeting, 15m circuit breaker quarantine, and foreground device timeout > 60s.
8. `hooks/guard_dispatch_contract.py`:
   - Formulates runnable `shlex.join` command to `dispatch_worker.py`.

### 4. Verification Protocol
- All tests must pass regression suites:
  ```bash
  python -m pytest tests/test_guard_device_bulkhead.py tests/test_guard_closeout_discipline.py tests/test_guard_broad_grep.py tests/test_guard_cronjob_safety.py tests/test_action_mandate.py tests/test_guard_dispatch_contract.py tests/test_dispatch_worker.py tests/test_claude_worker.py -q
  ```
  Expected: 257/257 passed.
