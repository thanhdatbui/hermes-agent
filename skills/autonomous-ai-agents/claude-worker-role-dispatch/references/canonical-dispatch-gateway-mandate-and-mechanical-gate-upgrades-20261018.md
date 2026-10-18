# Canonical Dispatch Gateway Mandate & Mechanical Gate Upgrades (18/10/2026)

## 1. Post-Mortem: Bypassing Canonical Gateway & Hallucinating Model Roles

### The Failure Mode
1. **Bypassing the Canonical Tool:** The system already had `D:/Taadaa/tools/dispatch_worker.py` specifically engineered to sanitize prompts into a single line, take pre/post diff snapshots, perform Attempt 1 (Haiku) -> Attempt 2 (O(1) retry) -> Tier 2 (Agy CLI) fallback. Despite this, the Coordinator bypassed `dispatch_worker.py` and directly called `claude_worker.py` with a multi-line raw prompt read from a text file.
2. **Windows CLI Argument Parsing Failure:** On Windows MSYS/cmd, passing un-sanitized multi-line strings to `claude -p` causes Claude Code CLI (`v2.1.281`) to drop instruction lines and misinterpret subsequent flags (like `--model claude-haiku-5-5`) as prompt text, printing advisory warnings:
   `"claude-haiku-5-5" isn't described by this version's model catalog...`
   and reaching max turns without editing files.
3. **Severe Hallucination & Blaming Model:** Instead of recognizing that it violated rules by bypassing `dispatch_worker.py` and passing a multi-line string, the Coordinator falsely claimed:
   - "Claude worker must be switched from Haiku 5.5 to Sonnet 5.5" (violating quota and role discipline).
   - "Quán tính mồm 3.5 cũ rích" (pure hallucination, no prompt or rule ever mentioned 3.5).
4. **User Interception:** The Operator immediately called out the violation:
   - Worker CLI runs Haiku 5.5 (`claude-haiku-5-5`) by design and has been running normally.
   - The syntax error was 100% caused by the Coordinator calling the CLI improperly instead of using the canonical dispatch gateway.
   - The system design was already correct; the Coordinator was caught actively breaking rules and making up excuses.

---

## 2. Invariant Rules: Worker Role & Dispatch Gateway

1. **Worker Role is PERMANENTLY Haiku 5.5 (`claude-haiku-5-5`):**
   - Worker = `claude-haiku-5-5` (fast, lightweight, quota-preserving).
   - Planner / Reviewer = `claude-sonnet-5-5` (deep architecture analysis and adversarial review).
   - NEVER suggest or switch Worker to Sonnet 5.5 due to a CLI warning or Reached Max Turns error.
2. **Single Dispatch Gateway is MANDATORY:**
   - All routine code repair/fix tasks MUST go through:
     ```bash
     python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<single-line prompt>"
     ```
   - CẤM gọi trực tiếp `claude_worker.py` hay `ag_cli.py` một cách thủ công rồi tự ý chọn model.
   - `dispatch_worker.py` automatically handles:
     - Prompt single-line sanitization (`" ".join(prompt.splitlines()).strip()`).
     - Pre/post execution snapshotting (verifying target file hash or git diff changed).
     - Attempt 1 (Haiku) -> Attempt 2 (O(1) focus prefix) -> Tier 2 Agy CLI fix fallback.

---

## 3. Mechanical Hard Gate Upgrades (Enforced in Code, Not Prompt)

The Operator mechanically upgraded the system's guard hooks to prevent Coordinator rule violations:

### A. Mechanical Block on `delegate_task` for Code Edits (`hooks/guard_dispatch_contract.py`)
- **Hard Gate #3:** Any call to `delegate_task` attempting a code edit is mechanically rejected at runtime unless explicitly tagged with `WORKER_CLI_EXHAUSTED` or `HAIKU_AND_AGY_FAILED`.
  ```python
  if not has_override:
      msg = "[HARD GATE #3 - CODE EDIT DISPATCH BLOCKED] delegate_task BỊ CẤM CHO TASK SỬA CODE! Bắt buộc thi công qua haiku_worker.py (6-15s O(1)). CẤM dùng delegate_task!"
      print(json.dumps({"action": "block", "message": msg}))
      sys.exit(0)
  ```
- **Investigation Budget Tightened:** Tasks under `INVESTIGATE` route have their call budget capped at **$\le 8$ tool calls** (reduced from $\le 15$), enforcing fast conclusions and immediate exit.

### B. Structured Canary Evidence Validation (`done_gate.py`)
- `has_recent_canary_evidence` parses `CANARY_PASSED_FLAG` JSON payload:
  - `runner_status` must strictly equal `"success"`.
  - `media_path` must exist on disk and its SHA256 must match `media_sha256`.
  - Task scope (`--task-scope single|wide`) must match the execution mode.

### C. Deep AST Console Window & Cron Policy Enforcement (`guard_cronjob_safety.py`)
- Analyzes subprocess calls via AST:
  - Forbids `CREATE_NEW_CONSOLE` (0x10).
  - Enforces `creationflags=subprocess.CREATE_NO_WINDOW (0x08000000)`.
  - Enforces `no_agent=True` (bool) for all cronjob creation/updates, forbidding unconstrained LLM loops in background cron jobs.
