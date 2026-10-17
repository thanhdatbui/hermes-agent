# Cronjob Console Window Suppression & Mechanical Gate Architecture

## 1. Context & Incident Analysis (17/10/2026)
During an active gaming session (TFT / LoL / War3) on the host machine (`Kibe`), a background janitor/sync cron task (`f_src-151 -> GDrive & Freed 45 files (190.27 MB)`) executed.
Because it invoked a console subsystem process without window suppression, Windows allocated a visible `cmd.exe` window (`C:\Windows\system32\cmd.EXE`) on the interactive desktop.
Even though the script finished in < 2 seconds, Windows automatically gave it foreground focus, tabbing the user out of their match.

When the user angrily demanded "Tắt cho tao", the coordinator initially misunderstood and paused all 54 cron jobs across the entire phone farm.
The user immediately corrected this: *"Tắt là tắt cái nháy nháy chứ sao lại tắt cron ? Bảo claude cli thiết kế gate khi mày viết cronjob. R bỏ khỏi prompt đi. Tóm lại rà soát luôn cái nào có gate r thì xoá bớt khỏi prompt mọi rule đi"*.

---

## 2. Mechanical Gate: `guard_cronjob_safety.py`
Instead of relying on prompt instructions that agents repeatedly violate, Claude Sonnet 5.5 designed an AST-based PreToolUse hook (`D:/Taadaa/tools/guard_cronjob_safety.py`).

### Verification & Policy Architecture:
1. **Tool Interception:** Intercepts `cronjob` (action: create/update) and `terminal`/`Bash`/`PowerShell` with `background=True`.
   - **False Positive Hardening (17/10/2026 Audit by Claude Reviewer):** For `cronjob`, ONLY inspect the `script` parameter (or actual command). DO NOT parse natural-language text in `prompt`, which causes false blocks on apostrophes or words like "Start".
2. **Top-Level Binary Lockdown:**
   - Denies: bare `python.exe`, `python3.exe`, `cmd.exe`, `start`, `.bat`, `.cmd`.
   - Requires: `pythonw.exe` or `powershell.exe -WindowStyle Hidden`.
3. **AST Inspection of Child Python Scripts:**
   - Parses the target script into Python AST.
   - Denies: `os.system()` and `os.popen()` (cannot hide console windows on Windows).
   - Requires: `creationflags` on all calls to `subprocess.run`, `subprocess.Popen`, `subprocess.call` containing `0x08000000` (`CREATE_NO_WINDOW`).
   - If missing: blocks the tool call immediately before execution with exact filename and line number.
4. **User Directive Parsing Precedence:**
   - When the user demands "Tắt cho tao" during an active game, distinguish Window Suppression ("tắt cái nháy nháy") from pausing farm business crons ("sao lại tắt cron"). Do not pause background jobs when the requirement is strictly UI window suppression.

---

## 3. Prompt Pruning Discipline: Mechanical Gate vs Prompt Prose
Once a mechanical gate enforces an invariant fail-closed, verbose warnings in system prompts / rule files become dead weight and should be pruned:

| Domain | Mechanical Gate | Prompt Action |
|---|---|---|
| Console Window Popups | `guard_cronjob_safety.py` | Prune all "cấm bật cmd" prose; the AST hook blocks creation. |
| Broad Recursive Scan | `guard_broad_grep.py` | Prune paragraphs prohibiting `os.walk`/`find`; keep 1-line routing hint (`inspect_machine.py <N>`). |
| Subagent Code Edits | `guard_dispatch_contract.py` | Prune lengthy warnings; hook blocks `delegate_task` on code edits automatically. |
| Large File Dumps | `guard_read_file_size.py` | Prune file reading rules; hook enforces `offset`/`limit`. |
| Pytest Scope | `guard_pytest_scope.py` | Prune test descriptions down to `focused test < 30s`. |
| Closeout Gate | `closeout_gate.py` & `pre-push.sh` | Prune 5-step 40-line review protocol down to single CLI invocation. |
