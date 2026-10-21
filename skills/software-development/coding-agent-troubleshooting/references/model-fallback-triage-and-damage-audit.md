# Model Fallback Triage & Workspace Damage Audit

Use this runbook when an operator suspects an unannounced model fallback occurred (e.g. Gemini Pro quota exhaustion triggering a fallback to GPT Luna or other models) and reports that the fallback agent panicked ("khóc lóc"), broke code ("phá hoại"), or paralyzed workflow.

## 1. Verify Fallback Event Without Speculation

Never guess whether a fallback occurred; verify with concrete timestamps and telemetry:

1. **Session-Level Model Audit (`session_search`)**:
   - Query recent sessions around the target timestamp:
     `session_search(query="<keyword>", limit=5)` or browse recent sessions.
   - Check the `model` field in the session metadata: if a session intended for `omni-worker` or `ag-gemini-pool-3` displays `gpt-5.6-luna`, fallback was active at the session coordinator level.
2. **Log Evidence (`agent.log`)**:
   - Search for fallback activations:
     `Fallback activated: <primary_model> → <fallback_model> (<provider>)`
   - Check upstream router status (OmniRoute `:20129` or 9Router `:20128`): look for `HTTP 503: ALL_TARGETS_SKIPPED` or `HTTP 429: Rate limit exceeded` across provider connection pools.

## 2. Distinguish Model Paralysis ("Khóc Lóc") from Destruction ("Phá Hoại")

Fallback models (notably Luna / GPT-5.6) often exhibit conservative paralysis under coordinator constraints:

- **Premature BLOCKED Declaration**: When a diagnostic tool (e.g. `inspect_machine.py`) times out (e.g. 45s), defensive models often abruptly halt and conclude `Trạng thái: BLOCKED có bằng chứng`, refusing to investigate further or draft patches.
- **Guard Collisions & Flailing**: When pressured to continue, a defensive coordinator may attempt unconstrained wide-disk scans (e.g. `os.walk`, `glob(recursive=True)`), which get rejected by host Coordinator Guards (`[GUARD_PYTHON_WALKER]`).
- **Worker Dispatch Failures**: May try dispatching workers with unmapped or deprecated model aliases (e.g. `claude-haiku-5-5`), or run into CLI timeouts (e.g. 600s).

**Key Insight**: Defensive flailing and refusal to act is NOT the same as code corruption. Do not assume the repository or devices are broken without running the damage audit below.

## 3. Systematic Repository & Workspace Damage Audit

Run this 4-step audit across all active repositories (`tiktok-luot nuoi acc`, `tools`, `Hotmail`, `Tiktok_Reg`, `AI-Tools`):

### Step A: Working Tree Inspection
```bash
git status --short
git diff --stat
```
Identify every unstaged or staged file modified during or around the fallback session.

### Step B: Syntax & Compilation Verification
Verify that every modified Python file compiles without syntax errors:
```bash
python -m py_compile <path/to/modified_file.py>
```

### Step C: Targeted Test Verification
Run focused pytest suites covering all changed modules:
```bash
pytest <tests_for_modified_files> -v --timeout=30
```
- If all tests pass (e.g. `133 passed, 4 skipped`), the changes made by fallback workers (such as Agy CLI `acc_16`) are functional patches (e.g. bounds checking, popup detection), not destructive regressions.

### Step D: Remote Integrity Audit
Check commit history to ensure no unapproved, untested commits were pushed to remote:
```bash
git log -n 5 --oneline
git diff origin/master..HEAD --stat
```
Confirm that no rogue commits were pushed during the incident.

## 4. Hardware & Farm Decoupling

When device errors (such as dropped USB connections or ADB offline states) coincide with a model fallback incident:

1. **Check System Uptime & Scheduled Reboot Windows**:
   - Inspect machine uptime via `psutil.boot_time()` or `uptime`.
   - Inspect `daily_reset.log` (e.g. `C:\Taadaa_Service\daily_reset.log`).
   - If scheduled reboots (e.g. 11:20 or 17:20) were skipped (`[SKIP]`) due to active device locks from ongoing runs, device instability and USB bus saturation accumulate over 15+ hours of continuous uptime.
2. **Check for Multiple ADB Daemon Conflicts**:
   - Inspect running processes for competing ADB servers on non-standard ports (e.g. port 5037 vs port 5038).
   - Dual ADB daemons polling the same physical USB hubs cause USB dropouts, completely independent of agent model behavior.
