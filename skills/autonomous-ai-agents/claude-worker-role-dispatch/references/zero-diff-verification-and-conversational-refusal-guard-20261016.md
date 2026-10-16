# Zero-Diff Verification & Conversational Refusal Guard in Worker Dispatch

> **Date:** 2026-10-16  
> **Component:** `D:/Taadaa/tools/dispatch_worker.py` and `D:/Taadaa/tools/claude_worker.py`  
> **Context:** Incident where Haiku CLI was dispatched via `dispatch_worker.py` but repeatedly output conversational questions ("What do you want done with this file?") without editing code. Because Claude CLI exited with code `0`, `dispatch_worker.py` falsely recorded `success: True` and exited with `0` despite zero file diff.

---

## 1. The False Exit-0 Conversational Refusal Trap

When Claude CLI is invoked in headless mode (`claude -p "<prompt>"`), it does not fail with a non-zero exit code when it decides to ask questions or refuse action. If it encounters:
- A dirty working tree with unrelated modified files,
- Unclear prompt phrasing or a prompt lacking an imperative action verb,
- An ambiguous contract,

it prints polite conversational prose (e.g. *"Nothing has been edited... What would you like me to do with this file?"*) and **exits with code 0**.

Treating `exit_code == 0` as proof of successful task completion is a critical architectural vulnerability that causes:
1. **Silent no-ops:** The caller believes the fix succeeded while `git diff` remains 0.
2. **Probe quota burn:** Probing tests or no-op runs waste 5-hour quota without modifying target files.
3. **Masked fallbacks:** The dispatch system fails to trigger Tier 2 fallbacks (such as `ag_cli.py fix`).

---

## 2. Hardening Architecture

### A. Pre/Post Content Hash Snapshot (`take_snapshot` & `verify_changes`)
Before invoking any worker (Haiku or Agy), `dispatch_worker.py` records a baseline snapshot:
- **File Mode (`--file <path>`):** Computes normalized SHA256 of the target file content:
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
  *Normalizing CRLF to LF prevents false diffs caused by Windows newline conversion.*
- **Git Repo Mode (no `--file`):** Computes SHA256 of `git diff -w --ignore-space-at-eol` to verify repo-level content changes.
- **Fail-Closed Baseline:** If no baseline snapshot can be taken (non-git directory and no target file), verification returns `(False, "no_snapshot_available_fail_closed")`.

### B. Worker Directive Injection (`claude_worker.py`)
To prevent Claude CLI from falling into conversational planning mode, `claude_worker.py` injects a mandatory directive via `--append-system-prompt` for the `worker` role:
```python
WORKER_DIRECTIVE = (
    "Non-interactive worker mode. Do not ask questions or propose plans. "
    "Apply the edit to the target file(s) with Edit/Write tool now. "
    "Ignore unrelated uncommitted files and never touch them. "
    "If the task cannot be done, print exactly BLOCKED: <reason> and make no edits."
)
```
- Line-anchored regex `(?im)^\s*blocked:\s*` matches explicit worker blockage while preventing false positives on words like `unblocked: yes`.
- When `BLOCKED:` is detected, `dispatch_worker.py` classifies the failure as `NEEDS_INPUT` and halts immediately without useless retries.

### C. Failure Classification Precedence
To ensure environmental and quota errors are never masked by diff checks, `classify_failure` evaluates in strict order:
1. **Execution / Environment errors:** `RC_PERMISSION`, `ENV_MARKERS` -> `ENV` (Halt immediately, no fallback).
2. **Quota exhaustion:** `RC_NOT_FOUND`, `QUOTA_MARKERS` -> `QUOTA` (Immediate fallback to Agy CLI).
3. **Turn/Time limits:** `MAX_TURNS_MARKERS`, `RC_TIMEOUT`, `TIMEOUT_MARKERS`.
4. **Diff / Output checks:** `BLOCKED:` -> `NEEDS_INPUT`; unchanged hash / conversational refusal -> `NO_DIFF`.

### D. Universal Verification across All Tiers
Tier 2 fallback (`ag_cli.py fix`) is subjected to the exact same pre/post snapshot verification:
- Both Haiku and Agy CLI must produce an actual verified content modification on the target file before `dispatch_worker.py` returns `exit 0`.
