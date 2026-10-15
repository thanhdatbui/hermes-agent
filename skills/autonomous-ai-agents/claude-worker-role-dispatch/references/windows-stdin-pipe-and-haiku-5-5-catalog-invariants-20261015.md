# Windows CLI Stdin Pipe Bug & Haiku 5.5 Model Catalog Invariants

**Date:** 2026-10-15  
**Component:** `D:/Taadaa/tools/claude_worker.py`, `D:/Taadaa/tools/haiku_worker.py`, Claude Code CLI on Windows 10/11

---

## 1. Incident Analysis: The Stdin Pipe Failure

### Symptom
When calling `claude_worker.py` or `haiku_worker.py`:
```text
{"event": "claude_execution", "correlation_id": "acb75b15", "latency_ms": 14336.0, "returncode": 1, "success": false, "model": "claude-haiku-5-5", "max_turns": 8, "role": "worker"}
"claude-haiku-5-5" isn't described by this version's model catalog; update Claude Code, or map it with behavesAs on a modelPicker row (or modelOverrides, if it is a provider id of a model this version knows)...
Error: Input must be provided either through stdin or as a prompt argument when using --print
```

### Root Cause
1. **The Stdin Trap on Windows:**
   In `claude_worker.py`, the command was structured as:
   ```python
   cmd = [
       claude,
       "-p",
       "--model", model,
       "--no-session-persistence",
       "--disable-slash-commands",
       "--max-turns", str(max_turns),
       "--allowedTools", role_cfg["allowed_tools"],
       "--dangerously-skip-permissions",
   ]
   # Prompt passed via stdin
   proc = subprocess.run(cmd, input=prompt_input, ...)
   ```
   On Windows, Node.js processes launched via `subprocess.run` often fail to recognize incoming piped data on `process.stdin` when `--print` (`-p`) expects either an immediate positional argument or an active streaming pipe. The CLI checks arguments before stdin is consumed and immediately aborts with:
   `Error: Input must be provided either through stdin or as a prompt argument when using --print` (exit code 1).

2. **Verification via Direct Positional Argument:**
   Executing the exact same command with the prompt argument placed directly on the CLI:
   ```bash
   claude -p "echo hello" --model claude-haiku-5-5
   ```
   Result: **`exit code 0`**, prints output immediately and cleanly.

---

## 2. Invariant: `claude-haiku-5-5` & `claude-sonnet-5-5` Model Names

### The Warning vs Reality
When passing `--model claude-haiku-5-5`, the CLI emits:
```text
"claude-haiku-5-5" isn't described by this version's model catalog; update Claude Code, or map it with behavesAs on a modelPicker row...
Warning: Advisor disabled — base model 'claude-haiku-5-5' has no advisor rank in the model catalog...
[claude-code:unrecognized_model] {"model":"claude-haiku-5-5","query_source":"sdk"}
```
**This is an advisory warning, NOT a fatal error.** The underlying proxy/Anthropic API accepts `claude-haiku-5-5` and `claude-sonnet-5-5` without issue.

### Hard Rule
- **NEVER** assume the model name is broken or invalid.
- **NEVER** hallucinate that the model should be renamed to legacy names like `claude-3-5-haiku` or `claude-3-7-sonnet`. Doing so will break system parity and user trust.
- The model strings on this system are strictly:
  - Worker: `claude-haiku-5-5`
  - Planner: `claude-sonnet-5-5`
  - Reviewer: `claude-sonnet-5-5`

---

## 3. Safe Execution Pattern

When invoking Claude CLI from Python on Windows:
```python
# Pass prompt directly as an argument after -p or at the end of args
cmd = [
    claude,
    "-p", prompt_text,
    "--model", model,
    "--no-session-persistence",
    "--disable-slash-commands",
    "--max-turns", str(max_turns),
    "--allowedTools", allowed_tools,
    "--dangerously-skip-permissions",
]
proc = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir, timeout=timeout)
```
If using a shell script or terminal command, wrap the prompt cleanly in double quotes:
```bash
claude -p "<prompt>" --model claude-haiku-5-5 --dangerously-skip-permissions
```
