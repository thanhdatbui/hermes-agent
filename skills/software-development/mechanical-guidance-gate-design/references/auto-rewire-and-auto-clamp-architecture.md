# Auto-Rewire & Auto-Clamp Gate Architecture: Eliminating Agent Paralysis & Loop Traps

## 1. Core Principle: Fail-Forward via Active Pivot
- **Fail-Stop Is Forbidden:** Pure passive denial (`action: "block"`) forces the agent into blind retries, token exhaustion, and loop paralysis.
- **Gate DENY = Self-Healing Trigger:** Every gate/hook denial must be converted into an automatic rewrite, clamp, or route forward.

## 2. Canonical Implementations

### A. Worker Entrypoint Auto-Rewire (`claude_worker.py` & `haiku_worker.py`)
- **Problem:** Direct invocations of Claude/Haiku worker without `--from-dispatch` returned exit code 126 (`[MECHANICAL TIER GATE VIOLATION]`), halting the workflow.
- **Solution:** Intercept unauthorized direct calls and forward 100% of arguments to `dispatch_worker.py`:
  ```python
  if role == "worker" and not (args.from_dispatch or os.environ.get("DISPATCH_TIER_CALLER") == "dispatch_worker"):
      dispatch_script = Path("D:/Taadaa/tools/dispatch_worker.py")
      print("[AUTO-REWIRE] ⛔ Direct Claude call diverted to dispatch ladder: Sol (T1) -> Agy (T2)...", file=sys.stderr)
      if dispatch_script.is_file():
          forward_cmd = [sys.executable, str(dispatch_script)]
          # append --file, --workdir, --timeout, --max-turns, prompt...
          res = subprocess.run(forward_cmd, cwd=args.workdir)
          return res.returncode
  ```

### B. Investigate Budget Auto-Clamp (`guard_dispatch_contract.py`)
- **Problem:** When an agent specifies an investigative budget > 8 calls (e.g. 10 or 15 calls), the hook rejected with `HARD_GATE_3_INVESTIGATE_BUDGET_EXCEEDED`, causing 600+ retry failures.
- **Solution:** Hook automatically clamps the budget to 8 and rewrites tool arguments:
  ```python
  if budget_value > 8:
      original_budget = budget_value
      budget_value = min(budget_value, 8)
      updated_args = rewrite_budget_in_args(args, original_budget, budget_value)
      print(json.dumps({
          "action": "rewrite",
          "rule_id": "HARD_GATE_3_INVESTIGATE_BUDGET_CLAMPED",
          "updated_args": updated_args,
          "notice": f"Auto-clamped investigate budget {original_budget} -> {budget_value} calls.",
      }))
      sys.exit(0)
  ```

### C. Console Window Matcher Narrowing (`guard_cronjob_safety.py`)
- **Problem:** Matcher `cronjob|terminal` blocked terminal commands running with `background=True` when `python` was used instead of `pythonw` (484 failures).
- **Solution:** Restrict pre-tool matcher in `config.yaml` to `cronjob` only via `manage_hermes_config.py set hooks.pre_tool_call[N].matcher cronjob`.

### D. Broad Root Scan O(1) Hinting (`guard_broad_grep.py`)
- When recursive scanning on `D:/` or `D:/Taadaa` is detected with farm terms (`machine`, `phone`, `m\d+`, `log`), inject deterministic O(1) fallback:
  `DÙNG LỆNH O(1): python D:/Taadaa/tools/inspect_machine.py <N>`.

### E. Closeout Gate `--skip-test` Auto-Rewire (`closeout_gate.py`)
- **Problem:** When an agent lazily passes `--skip-test` in repo mode, Closeout Gate previously threw a fatal exit 1, logged audit `TEST_SKIPPED` with score 0, and blocked session completion.
- **Solution:** Closeout Gate automatically suppresses the `--skip-test` flag, logs a warning, and forces automated test execution instead of failing-stop:
  ```python
  if args.skip_test:
      warn("[Gate] AUTO-REWIRE: --skip-test bị cấm trong repo mode! Đã tự động bỏ qua cờ này và cưỡng chế chạy test tự động để thẩm định.")
      args.skip_test = False
  ```
  This eliminates artificial 0-score rejections and guarantees that closeout proceeds directly to verified test evaluation.

## 3. Closeout Gate Stability & Remediation Invariant
- **Empirical Performance:** 80% of recent runs pass in 1-2 rounds (3-7 minutes). Sol Repair Monopoly (`sol_repair.py`) successfully handles Strikes 1 & 2 autonomously.
- **Do Not Touch Rule:** Stable gates with zero persistent failures must remain untouched to prevent regressions.

## 4. Anti-Whining & Zero-Paralysis Action Invariants
- **Do Not Explain When Commanded to Execute:** When the user explicitly orders execution ("R làm đi", "fix nốt đi"), immediately perform the edits and verification. Do not produce verbose explanations, reiterate block reasons, or ask for redundant permission.
- **Auto-Rewire Over Fail-Stop:** Every guard or gate failure pattern must be converted into an automatic rewrite, clamp, or route forward. The agent must never report BLOCKED without an active, deterministic pivot path.
- **Test Alignment Verification:** When modifying gate warning/error messages (such as `--skip-test is forbidden in repo mode`), verify that regression tests asserting those exact strings remain intact.

## 5. Claude CLI Architecture Consensus: Safe Auto-Rewire vs Mandatory Fail-Fast
- **The Core Rule**: Only auto-fix/auto-rewire when the transformation preserves original intent and does NOT alter permissions, execution tiers, or target scopes. Otherwise, fail-fast immediately with copy-pasteable `REQUIRED_ACTION_O1`.
- **Safe to Auto-Rewire / Auto-Inject**:
  * *Investigate Route Default Budget*: When `delegate_task` is called for read-only investigation without a `BUDGET:` tag, auto-inject `BUDGET: <= 8 calls` with `action: "rewrite"` and notice flag `AUTO_INJECTED_DEFAULT`. (Never inject for code-edit routes).
  * *Console Window Suppression (`CONSOLE_WINDOW`)*: On Windows, auto-merge `creationflags |= 0x08000000` (`CREATE_NO_WINDOW`) in background subprocesses to prevent console popups from stealing OS focus.
- **Strictly Forbidden to Auto-Rewire (Must Fail-Fast with REQUIRED_ACTION_O1)**:
  * *Code Edit via `delegate_task` (`subagent_edit_blocked`)*: `dispatch_worker.py` enforces a completely different execution contract (Context Pack, single anchor, worker tier ladder). Rewiring implicitly changes the executor without review. Must DENY with pre-filled `dispatch_worker.py` command containing the target file.
  * *Root Disk Scanning (`GUARD_SEARCH_FILES_ROOT` / `GUARD_DANGEROUS_ROOT`)*: NEVER auto-narrow broad search paths (e.g. `D:/Taadaa` -> `D:/Taadaa/tools`). Guessing scope risks returning incomplete/false results silently and violates Scope Lock. Must DENY with copy-pasteable command narrowed to cwd or machine log.
  * *Device Locks (`GUARD_DEVICE_LOCK_REQUIRED`)*: NEVER auto-acquire locks. Locks belong strictly to `host+pid+lock_id`. Must DENY with sample `with_device_lock.py --machine <N> -- ...` command.
- **Guidance Placement Hierarchy**:
  * *`rules.json` (GuardGate)*: Use when violations are detectable via regex/AST, binary pass/fail, and have heavy operational consequences (I/O freeze, device collision, console stealing). Intercepts at tool invocation time.
  * *Dynamic Skill Routing (`record_skill_knowledge.py`)*: Use for operational context (tier selection, context packs, budget rationale). Injected into prompt before tool call to minimize initial blocks.
  * *Promotion from Skill to Rule*: If repeated blocks persist despite skill injection (e.g. >20 blocks in 6h), promote from skill guidance to mechanical gate rule with pre-filled `REQUIRED_ACTION_O1` template.


