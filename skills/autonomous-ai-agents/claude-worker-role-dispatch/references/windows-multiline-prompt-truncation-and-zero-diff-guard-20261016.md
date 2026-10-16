# Windows Multiline Prompt Truncation & Zero-Diff Verification Guard (16/10/2026)

## 1. Context & The Mystery of Haiku's "Conversational Evasion"

In a production session, Haiku 5.5 was invoked 4 times via `dispatch_worker.py` to apply code changes to `claude_quota_guard.py` and `dispatch_worker.py`. In each run, Haiku outputted conversational analysis asking:
> *"I found `dispatch_worker.py`... but your message only names the file and doesn't say what to do with it. What do you want done? Tell me the goal..."*

Because Claude Code CLI exited with code `0`, naive dispatchers marked the task as `success: True`, while `git diff` showed 0 modified lines on the target file.

---

## 2. Root Cause Analysis: Two Interlocking Flaws

### Flaw A: The Windows Node.js / MSYS Multiline Truncation Trap
In `claude_worker.py`, prompt construction previously did:
```python
def build_prompt(prompt: str, target: str | None) -> str:
    if not target:
        return prompt
    return f"Target file: {target}\n\n{prompt}"
```
On Windows, when `claude` (which resolves to `claude.cmd` launching Node.js) is called via `subprocess.run([claude, "-p", prompt_input, ...])`, any unescaped newline `\n` in command-line arguments causes the Windows batch/cmd parser or Node.js argument parser to truncate the argument after the first line.
As a result, Claude CLI literally received only:
```text
Target file: dispatch_worker.py
```
The actual task instruction below `\n\n` was completely dropped before reaching the LLM! Haiku asked "what do you want done?" because it literally never received the instructions.

### Flaw B: Untrusted Exit Code 0 & Missing Zero-Diff Verification
When a worker outputs conversational questions without calling `Edit` or `Write` tools, Claude CLI exits with returncode `0`. 
Treating `rc == 0` as success without verifying that target files actually changed created a silent failure loop where the agent believed the code was fixed.

---

## 3. Engineering Hardening Implemented

### 1. Mandatory Single-Line Sanitization & System Directive (`claude_worker.py`)
In `claude_worker.py`:
```python
# Strip all newlines and collapse whitespace so Windows CLI arguments are never truncated
prompt_input = " ".join(build_prompt(args.prompt, args.file).splitlines()).strip()

# Inject non-interactive directive via --append-system-prompt
WORKER_DIRECTIVE = (
    "Non-interactive worker mode. Do not ask questions or propose plans. "
    "Apply the edit to the target file(s) with Edit/Write tool now. "
    "Ignore unrelated uncommitted files and never touch them. "
    "If the task cannot be done, print exactly BLOCKED: <reason> and make no edits."
)
if role == "worker":
    cmd += ["--append-system-prompt", WORKER_DIRECTIVE]
```

### 2. Snapshot & Verification Engine (`dispatch_worker.py`)
Before executing any worker tier (Haiku or Agy):
- **Pre-execution Snapshot:** Compute SHA256 of target file normalizing line endings (`data.replace(b"\r\n", b"\n")`).
- **Post-execution Verification:**
  * If `rc == 0` but target file hash is unchanged: reject as `NO_DIFF` (`target_file_unchanged`).
  * If output matches anchored `(?im)^\s*blocked:\s*`: reject as `NEEDS_INPUT`.
  * If output contains conversational refusal markers (`nothing has been edited`, `what do you want done`): reject as `NO_DIFF`.
  * If no snapshot baseline exists: fail-closed (`no_snapshot_available_fail_closed`).
- **Classification Precedence:** System errors (`ENV`, `QUOTA`, `TIMEOUT`, `MAX_TURNS`) are evaluated first to prevent swallowing quota drops into `NO_DIFF`.
- **Enforced Tier Progression:**
  * Haiku Attempt 1 (10-20s) -> if `NO_DIFF`, Haiku Attempt 2 with O(1) single-line prompt.
  * If Attempt 2 still fails `NO_DIFF`, escalate to Agy CLI fix (`ag_cli.py fix`).
  * Agy CLI is subject to the identical pre/post diff verification before returning exit code 0.

---

## 4. Empirical Verification Evidence
Testing after the fix:
1. `In D:/Taadaa/tools/dispatch_worker.py: change TIMEOUT_GRACE_SECONDS = 15 to 16`:
   - Haiku Attempt 1 completed in **19.5s** with diff verified: `exit_code: 0, success: true`.
2. `In D:/Taadaa/tools/dispatch_worker.py: change TIMEOUT_GRACE_SECONDS = 16 back to 15`:
   - Haiku Attempt 1 completed in **21.8s** with diff verified: `exit_code: 0, success: true`.
Zero conversational refusal, zero false exit-0 successes.
