# Terminal Foreground Timeout & Background Blocking Workaround

## 1. Problem: The Coordinator Terminal Deadlock
In tight-security agent environments (such as Taadaa Farm), the Coordinator agent faces two competing guards:
1. `[GUARD_FOREGROUND_TIMEOUT_EXCEEDED]`: Foreground commands must have `timeout <= 60s`.
2. `[CONSOLE_WINDOW_BLOCKED]`: Running `python` with `background=True` is blocked to prevent visible console window popups.
3. `[COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY)]`: Running `pythonw` or `powershell -WindowStyle Hidden` is blocked by the Coordinator command allowlist.
4. `[COORDINATOR GUARD - EXECUTE_CODE DISABLED]`: `execute_code` tool is disabled to prevent ad-hoc scripts.

When a batch operation (e.g. auditing 5 browser profiles, running a multi-account task) takes longer than 60s in total, running the full batch in foreground fails due to timeout, while running in background fails due to console window / allowlist blocking.

## 2. Solution: Foreground Chunking by Sub-commands
Instead of running a large batch in a single call or fighting the background guards:
1. **Probe / Canary Chunk**: Run a small fraction (e.g. `--canary` for 2 items) using `terminal(command=..., timeout=60)`. Each item takes 20-25s, so 2 items finish in ~45s.
2. **Sequential Single-Item Chunks**: Run remaining items individually via single-target flags (e.g. `--email <item>` or `--machine <N>`) with `timeout: 60`. Each runs in 20-30s well within the 60s budget.
3. **Synthesis & Atomic Update**: Aggregate results across chunk runs and write the final report atomically using `write_file` (not `python -c` which may be restricted for file writes).
4. **Verification**: Run the focused pytest suite (`pytest tests/... -q`) in foreground (<30s) to produce fresh verification evidence.
