# Prompt-Contract Desync & Shell Scanner False-Positive Triage

## 1. Context & Operational Symptoms
During 6-hour farm compliance audits, compliance watchdogs repeatedly reported high failure counts:
- `[Anti-Scan Terminal] GUARD_DANGEROUS_ROOT`: 34+ blocks per window.
- `[Worker Dispatch] subagent_edit_blocked`: 23+ blocks per window, cascading into `NEEDS_INPUT`, `NO_DIFF`, and `TIMEOUT`.

Investigation revealed two coupled architectural traps:
1. **Prompt-to-Gate Semantic Desync**: The system prompt (`SOUL.md`) instructed the Coordinator to delegate all code changes via `delegate_task`, while the pre-tool gate (`guard_dispatch_contract.py`) strictly enforced a mechanical block on code edits via `delegate_task`, mandating `dispatch_worker.py`.
2. **Shell Scanner False Positives in Python Script Invocations**: Command-line regex scanners (`FIND_SCAN`, `contains_dangerous_root`) inspected entire command strings without command-position discrimination, treating Python comments (`# Find center bounds`) and integer division (`// 2`) as dangerous root scans.

---

## 2. Core Invariants & Architectural Patterns

### A. Two-Ended Alignment (Prompt Authority vs Mechanical Gate)
- **Anti-Pattern:** `SOUL.md` directs the Coordinator: *"Mọi việc phát triển code... BẮT BUỘC do Worker subagent thực hiện qua delegate_task"*, while `guard_dispatch_contract.py` denies `delegate_task` with `subagent_edit_blocked`. Furthermore, the hook guidance suggested override keywords (`ALLOW_SUBAGENT_CODE_EDIT`), tempting agents to bypass the gate and spawn unguided subagents that stall on `NEEDS_INPUT` or `TIMEOUT`.
- **Rule:**
  1. **Source Prompt Synchronization:** `SOUL.md` must explicitly mandate `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<prompt>"` for all code edits, reserving `delegate_task` strictly for read-only investigation (`budget <= 8 calls`).
  2. **Zero-Loophole Hook Guidance:** Remove suggestions for bypass keywords from hook denial guidance. Provide exclusively the verified, copy-pasteable terminal command targeting `dispatch_worker.py`.

### B. Command-Position Discrimination for Shell Scanners
- **Anti-Pattern:** Using naive substring regexes like `(?<![\w.-])find(?:\.exe)?\s+[^\n]*` and `/{1,2}` on arbitrary command lines:
  - Comments in inline Python scripts (`# Find center phone bounds`) trigger `FIND_SCAN`.
  - Python arithmetic operations (`mid_x = (x1 + x2) // 2` or `ratio = a / b`) match Unix root `/` or `//`.
  - Self-referential deadlocks: Running `dispatch_worker.py ... "Fix FIND_SCAN..."` is blocked by `FIND_SCAN` itself!
- **Rule:**
  1. **Strict Command Position:** Shell command scanners (`find`, `grep`, `rg`) must require beginning of line or shell command operators:
     ```python
     FIND_SCAN = re.compile(
         r"""
         (?:^|[;&|`$()]\s*|\b(?:sudo|env)\s+)
         find(?:\.exe)?
         \s+
         (?:-[a-zA-Z]|\.|\/|[a-zA-Z]:)
         [^\n]*
         """,
         re.I | re.X,
     )
     ```
  2. **Python Subprocess Isolation:** When the command line invokes Python (`^\s*python(?:\d+)?(?:\.exe)?\s+`), bypass all shell tool scanners (`find`, `grep`, `rg`, `Get-ChildItem`). Rely exclusively on AST/regex checks for Python filesystem APIs (`PYTHON_SCAN`: `os.walk`, `Path.rglob`, `glob...recursive=True`).
  3. **Division vs Root Separation:** Root path checks must enforce `(?<!/)(?:^|[\s'\"`(=])/(?:[\s'\"`\)]|$)(?!/)` and explicitly exempt commands starting with `python` from standalone `/` matching.

### C. Safe Closeout Scope Alignment & Invariant Enforcement
- **Anti-Pattern:** Attempting to close out a session by passing `--files` that mismatch the committed diff scope between `base_ref` and `HEAD`, or introducing logic changes without step comments in files audited by `check_step_by_step_structure`.
- **Rule:**
  1. **Strict Scope Equality:** The `--files` passed to `closeout_gate.py` must match 100% of the modified files between `--base` and `HEAD`. If uncommitted files were committed together, include all committed targets in `--files`.
  2. **Step Comment Mandate:** When editing files subject to `check_step_by_step_structure`, any added logic block $\ge 15$ lines must contain explicit `# === Step: ... ===` comments to satisfy the GuardGate invariant.
  3. **Subprocess Hook Freshness vs Gateway Memory:** Pre-tool guard scripts (`hooks/guard_*.py`) are executed as fresh subprocesses on every tool call and reflect disk changes instantly without Gateway restarts. Gateway restart is strictly reserved for core engine modules in RAM.
