# Antigravity CLI (`ag_cli.py`) Dispatch & Flag Traps

## 1. Subcommand Argument Schema
In `D:/Taadaa/tools/ag_cli.py`:
- `ask` parser: accepts `--prompt`, `--file`, `--model`, `--workdir`, `--timeout`, and `--profile`.
- `fix` parser: accepts `--prompt`, `--file`, `--model`, `--workdir`, and `--timeout`. **Does NOT accept `--profile`.**

### Error Manifestation
```bash
python D:/Taadaa/tools/ag_cli.py fix --profile acc_01 "Tạo file..."
# Output:
# usage: ag_cli.py [-h] {ask,fix,models,pool-status,init-profile} ...
# ag_cli.py: error: unrecognized arguments: --profile
```

### Correct Pattern
When fixing or scaffolding code, omit `--profile`:
```bash
python D:/Taadaa/tools/ag_cli.py fix --workdir "D:/Taadaa/site ban hang clone" --timeout 240 "<focused_task>"
```
The pool scheduler automatically selects the best profile via LRU while respecting `.profile.lock` leases and cooldown states.

## 2. Multi-File Module Scaffolding Timeout
Attempting to scaffold an entire 5-file module (e.g. SQLite DB, evaluator, sync adapter, FastMCP server, and full test suite) in a single turn triggers exit code 124 (timeout > 180s).
- **Rule**: Decompose into bite-sized 1-2 file deliveries.
- Phase 1: Storage engine (`db.py`) + Domain Evaluator (`evaluator.py`).
- Phase 2: FastMCP server (`server.py`) + Sync adapter (`sync_adapter.py`).
- Phase 3: Pytest test suite (`tests/test_mcp_server.py`).
- Always run long CLI tasks via `terminal(background=True, notify_on_complete=True)` with timeout $\ge 240\text{s}$.
