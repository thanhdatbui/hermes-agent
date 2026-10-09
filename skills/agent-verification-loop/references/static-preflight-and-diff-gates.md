# Static Preflight, Diff Guard, and Pyright Regression Gates

Recipes and pitfalls for constructing fast preflight and anti-regression gates (Ruff, Pyright, AST Diff Guard) alongside pytest suites.

---

## 1. Pyright Unbound Variable Gate (`pyrightconfig.gate.json`)

When configuring a strict, minimal Pyright gate for legacy or untyped Python codebases (to catch runtime `UnboundLocalError` without triggering hundreds of optional type annotations):

### Pitfall: Invalid setting name
- Specifying `"reportPossiblyUnbound": "error"` produces a configuration warning:
  `Config contains unrecognized setting "reportPossiblyUnbound"`.
- Pyright recognizes the following exact rule names:
  - `"reportPossiblyUnboundVariable": "error"` — flags variables defined in only some branches of `if/else` or `try/except` before being read.
  - `"reportUnboundVariable": "error"` — flags variables referenced before any assignment in all execution paths.
  - `"reportUndefinedVariable": "error"` — flags undeclared or unimported names.

### Minimal, zero-noise gate configuration
```json
{
  "typeCheckingMode": "off",
  "reportPossiblyUnboundVariable": "error",
  "reportUnboundVariable": "error"
}
```
Run with:
```bash
pyright --project pyrightconfig.gate.json <target_files_or_directories>
```
Runs in < 1 second and fails (exit code 1) on branch-unassigned variables that standard linters miss.

---

## 2. Fast Linter Syntax & Undefined Gate (Ruff)

Before launching slower type-checkers or test suites, run a sub-second check for syntax errors and unimported/undefined identifiers:
```bash
ruff check --select E9,F821 <target_files>
```
- `E9`: Syntax errors, indentation errors, I/O errors.
- `F821`: Undefined name references.

---

## 3. AST Diff Guard (Caller Omission & Safety Checks)

An AST-based diff guard verifies that changes in the current worktree do not introduce caller regressions:
1. **Caller omission check:** Inspects `git diff` against BASE (`HEAD`), detects functions whose parameter signatures changed (arity or argument names), scans the AST of caller modules, and flags any call site that was not updated in the diff unless annotated with `# regress-ok`.
2. **High-risk safety wrapping:** Inspects modified functions to verify high-risk device/network calls (e.g. `dump_hierarchy`, `_capture_xml_text`) are properly guarded by `try/except` blocks or null-checks.

---

## 4. Large Workspace Search and Timeout Pitfall

In repositories with active test runs, run logs, `.ai-runs`, and pytest caches (e.g., `python_runner/runs/`, `__pycache__`, `.pytest_cache`):
- **Pitfall:** Unbounded recursive searches like `grep -rn "pattern" .` or un-scoped AST walks can hang for hundreds of seconds or hit tool execution timeouts (900s).
- **Rule:** Always prune or exclude artifact directories:
  ```bash
  grep -rn --exclude-dir={runs,.ai-runs,__pycache__,.pytest_cache} "pattern" python_runner/
  ```
  Or restrict AST traversal to scoped code packages (e.g., `python_runner/core/`, `python_runner/flows/`).
