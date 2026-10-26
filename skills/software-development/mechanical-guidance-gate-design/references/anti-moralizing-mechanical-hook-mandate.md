# Anti-Moralizing & Mechanical Hook Mandate (Sửa Hook Thay Vì Viện Cớ Kỷ Luật)

## Core Philosophy

When a safety invariant or operational constraint is breached (e.g. background automation triggering screen flickers, unsuppressed console windows, or focus drops):
- **NEVER offer moralizing, disciplinary, or personal excuses** (e.g. *"Dạ do 3 lỗ hổng kỷ luật và ý thức..."*).
- The user strongly rejects lectures and self-criticism: *"sửa hook chứ đéo phải kỷ luật lồn cặc gì cả"*.
- **The Iron Principle:** If an invariant can be broken by human or agent oversight, the defect is **mechanical**, not moral. Fix the mechanical gate/hook (`guard_cronjob_safety.py`, `guard_broad_grep.py`, etc.) so that the violation becomes structurally impossible to execute.

---

## The 3-Step Incident Resolution Sequence

### Step 1: O(1) Instant Live Relief (Stop Ongoing Disturbance First)
Before writing any code or analyzing architecture, inspect the actual live physical state and extinguish the active disruption:
- **Do NOT claim "Đã xử lý triệt để" while the user's screen is still actively flickering.**
- Query live processes on the target machine:
  `Get-Process | Where-Object { $_.Name -match 'cmd|powershell|conhost' }`
- Terminate stale transparent overlays:
  `Stop-Process -Name cua-driver -Force` (removes 1920x1080 topmost invisible overlay causing DirectX DWM stutter).
- Pause runaway watchdogs or background transfer scripts:
  `cronjob(action='pause', job_id=...)`

### Step 2: Consult Claude CLI for Mechanical Architecture
Do not guess regexes or invent brittle ad-hoc string checks. Consult Claude CLI directly for gate architecture:
```bash
claude -p "Context & symptom... Require AST/pattern check logic and fail-closed rule design." --model haiku
```
- Use `--model haiku` for fast, sharp architectural consultations (<30s).
- Extract the recommended AST nodes, parser boundaries, and fail-closed policy.

### Step 3: Implement, Test & Verify Fail-Closed Hook
1. **Patch the Hook**:
   - Update AST scanner (`scan_script`) to traverse `subprocess.run/Popen/call` arguments.
   - Update segment scanner (`check_segment`) for shell commands.
   - Enforce `-WindowStyle Hidden` for any invocation involving SSH / remote hosts / PowerShell.
2. **Write Dual-Path Unit Tests**:
   - Test unsafe cases -> MUST be blocked (`res['action'] == 'block'`).
   - Test safe cases -> MUST be allowed (`res['action'] == 'allow'`).
3. **Execute Full Test Suite & Closeout Gate**:
   - Run focused pytest (`pytest tests/test_guard_cronjob_safety.py`).
   - Run `closeout_gate.py` with score $\ge 85$.
   - Push via `safe_push.py`.

---

## Pitfalls & Lessons

- **Remote SSH OpenSSH Subsystem Trap**:
  Local Python `sitecustomize.py` patches local child processes, but does NOT protect remote Windows OpenSSH commands. When dispatching `ssh admin-farm 'powershell ...'`, Windows OpenSSH Server executes through `cmd.exe /c powershell...` and creates an unsuppressed `conhost.exe`. Remote PowerShell invocations MUST explicitly include `-WindowStyle Hidden` in the command string itself.
- **Premature Resolution Announcements**:
  Never declare an issue resolved based only on code patches while background worker threads (already loaded in RAM) continue dispatching commands from an ongoing batch run. Check process counts (`conhost.exe`, `ssh.exe`) before confirming relief.
