# Non-Interactive Account Row CLI Prompt & Follow-Hook Timeout

## Symptom & Incident Signature
- Farm Alert: `• Script: tiktok-follow`, `status: timeout`, `reason: follow-timeout`.
- In parent feed session log:
  ```json
  {"step": "follow-hook", "action": "run_follow", "result": "started", "extra": {"command": ["...\\python.exe", "...\\run_follow.py", "--machine", "74"], "follow_timeout_seconds": 1200.0}}
  ```
- After exactly 1200 seconds (hard timeout), child process is killed:
  ```json
  {"machine": 74, "row": 2, "status": "timeout", "reason": "follow-timeout", "followed_count": 0, "failed": 1}
  ```
- Device screenshot shows TikTok Feed ("Đề xuất") untouched, no search navigation, no logs emitted by child process.

## Root Cause
- When `--account-row-index` is omitted from the CLI invocation (`run_follow.py --machine <N>`), `_prompt_account_row()` attempts to ask the operator interactively:
  ```python
  raw = input(f"Chọn account row ({options_str}, default {default}): ").strip()
  ```
- In headless background/cron execution (spawned via `subprocess.Popen` without a TTY), `input()` blocks indefinitely waiting for stdin input that will never arrive.
- The process hangs at startup before any device connection or logging occurs, until the parent session kills it at 1200s.

## Rule & Safe Pattern
1. **Non-interactive detection & EOF fallback**:
   `_prompt_account_row` must check `sys.stdin.isatty()` before calling `input()`, safely handling `None` or missing attributes, and catching `EOFError`:
   ```python
   is_interactive = False
   try:
       is_interactive = bool(sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty())
   except Exception:
       is_interactive = False

   if not is_interactive:
       logger.warning("Môi trường non-interactive (not sys.stdin.isatty()), tự động chọn default account row %s cho máy %s", default, machine)
       return default

   try:
       raw = input(f"Chọn account row ({options_str}, default {default}): ").strip()
   except EOFError:
       logger.warning("EOF trên stdin khi prompt account row, fallback về default account row %s cho máy %s", default, machine)
       return default
   ```
2. **Pytest capture pitfall**:
   Trong pytest, `sys.stdin` mặc định là `_pytest.capture.DontReadFromInput`, có `isatty() == False`.
   - Các unit test kiểm thử hành vi tương tác (`input() == "abc"` hoặc chọn row) BẮT BUỘC phải mock `monkeypatch.setattr(sys.stdin, "isatty", lambda: True)` kèm `import sys`.
   - Các unit test kiểm thử non-interactive fallback phải mock `monkeypatch.setattr(sys.stdin, "isatty", lambda: False)` và kiểm tra `input()` tuyệt đối không được gọi (`pytest.fail`).
3. **Explicit CLI argument**:
   Callers (e.g., `_run_follow_hook` in parent feed runner, canary scripts, `run-follow.ps1`) must always supply `--account-row-index <N>` explicitly rather than relying on interactive prompt fallbacks.
3. **Execution speed & targeting**:
   When investigating root cause on farm machines, never run broad file searches or recursive walks across `/d/Taadaa/` (which contains massive OneDrive syncs, logs, and runtimes). Target searches strictly to `D:/Taadaa/tiktok-follow` or the specific machine run artifact folder `D:/Taadaa/runtime/kibe/live/<date>/.../machines/machine_<N>/`.
