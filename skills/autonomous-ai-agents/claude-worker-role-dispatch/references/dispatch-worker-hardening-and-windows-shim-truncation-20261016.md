# Dispatch Worker Hardening and Windows Shim Truncation (16/10/2026)

## 1. Incident: The "Haiku Lazy Conversational Refusal" Mystery
When calling `dispatch_worker.py` on Windows to edit code files, Haiku 5.5 consistently returned exit code 0 without modifying the target file, printing conversational responses:
> *"I read dispatch_worker.py, but your message only says 'Target file: dispatch_worker.py'. It doesn't say what you want done, so I haven't changed anything. What do you want done with this file?"*

### Root Cause Analysis (Confirmed by Claude Sonnet Reviewer)
1. **Windows MSYS / cmd.exe Shim Newline Truncation:**
   - `shutil.which("claude")` on Windows resolves to `hermes\bin\claude.CMD`.
   - `cmd.exe` passes arguments to Node.js/Python via `%*`. In `cmd.exe`, a newline `\n` in a command line argument cuts off the entire argument string at the first newline!
   - `build_prompt(prompt, target)` formatted the prompt as:
     `f"Target file: {target}\n\n{prompt}"`
   - Result: Claude CLI only saw the first line (`Target file: <path>`) and lost all subsequent instructions.
2. **False Success on Exit Code 0:**
   - Claude CLI exits with 0 even when it only prints a conversational refusal/question.
   - `dispatch_worker.py` originally checked `if rc == 0: return 0`, treating a no-op conversational refusal as success.

---

## 2. Hardening Measures Implemented

### A. Single-Line Prompt Sanitization (`claude_worker.py`)
To prevent `cmd.exe` argument truncation, all prompts passed to `claude -p` must be sanitized to a single line:
```python
prompt_input = " ".join(build_prompt(args.prompt, args.file).splitlines()).strip()
```

### B. Worker Directive (`claude_worker.py`)
Injected via `--append-system-prompt` exclusively for the `worker` role:
```python
WORKER_DIRECTIVE = (
    "Non-interactive worker mode. Do not ask questions or propose plans. "
    "Apply the edit to the target file(s) with Edit/Write tool now. "
    "Ignore unrelated uncommitted files and never touch them. "
    "If the task cannot be done, print exactly BLOCKED: <reason> and make no edits."
)
```

### C. Zero-Diff Gate & Normalized Hash Comparison (`dispatch_worker.py`)
Pre- and post-execution snapshots check normalized SHA-256 (normalizing `\r\n` to `\n`):
```python
def _normalize_content(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")

def _file_hash(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        return hashlib.sha256(_normalize_content(path.read_bytes())).hexdigest()
    except OSError:
        return None
```
- If `rc == 0` but target file hash is unchanged (`target_file_unchanged`), it is classified as `NO_DIFF`.
- If target file is deleted, `target_file_deleted` returns `False` (deletion is rejected as success unless explicitly expected).
- If snapshot cannot be taken (non-git and no file), it fails closed with `no_snapshot_available_fail_closed`.

### D. Unrelated Files Changed Guard (Git Fingerprints)
When `--file` is supplied in a git repository:
- `take_snapshot` records `git_fingerprints` for all dirty/untracked files.
- `verify_changes` asserts that ONLY the specified target file was touched. Any side effects to other files return `(False, "unrelated_files_changed")`.

### E. Centralized Fallback & Exit Code Split (`EXIT_QUOTA_BLOCKED = 125`)
To eliminate nested duplicate fallbacks (where `claude_worker` runs Agy and then `dispatch_worker` runs Agy again):
- `claude_worker.py` adds `--no-fallback`. When set, quota rejections return exit code `125` (`EXIT_QUOTA_BLOCKED`) immediately.
- `dispatch_worker.py` passes `--no-fallback` to `haiku_cmd` and centrally manages the fallback ladder:
  * Exit 125 or quota markers -> `QUOTA` -> escalates to `ag_cli fix`.
  * Exit 126/127 -> `ENV` -> stops immediately (no Agy fallback). `PermissionError` is mapped to `RC_PERMISSION = 126`.
  * Line-anchored `(?im)^\s*blocked:` -> `NEEDS_INPUT` -> stops immediately (no retry, no Agy fallback) on both attempt 1 and attempt 2.

### F. Telemetry & Correlation ID
`main()` generates a unified `correlation_id = uuid.uuid4().hex` and passes it through all audit logging records, linking attempt 1, retries, and fallback runs into a traceable chain.

### G. Robust Fallback Command (`run_agy`)
When escalating to `ag_cli fix`, all parameters are properly propagated:
```python
def run_agy() -> tuple:
    cmd = [sys.executable, AG_CLI, "fix", "--workdir", workdir, "--timeout", str(args.timeout)]
    if args.file:
        cmd += ["--file", args.file]
    return run_tool(cmd + ["--", args.prompt], cwd=workdir, timeout=args.timeout)
```

### H. Cumulative Baseline Check on Attempt 2
Attempt 2 compares against `snap1` (the initial pre-dispatch snapshot), ensuring that partial edits in attempt 1 combined with attempt 2 are properly credited.

---

## 3. Verification & Test Suite
- `tests/test_claude_worker.py`: 32/32 tests pass.
- `tests/test_dispatch_worker.py`: 11/11 tests pass covering CRLF normalization, failure classification hierarchy, snapshot verification, anchored BLOCKED markers, PermissionError mapping, correlation ID consistency, and unrelated-file protection.
- Total 43/43 tests pass across the dispatch subsystem.
- Reviewed and APPROVED by Claude Sonnet 5.5 (`--role reviewer`).
