# Compliance Watchdog Fidelity: Mock Test Sanitization, Timezone Normalization, and Three-Way Script Sync

## 1. Context & Operational Symptoms
During 6-hour fleet audits, compliance watchdogs (such as `gate_compliance_watchdog.py`) frequently emit false-positive `FAIL` alerts (e.g. `G3 Worker Dispatch Gate: FAIL (vi phạm: 230)`, `G7 Anti-Scan Terminal Guard: FAIL (vi phạm: 218)`) despite zero user-facing regressions on the farm.
Investigation revealed three coupled architectural traps:
1. **Mock Test Telemetry Pollution**: Unit tests testing guard intercepts (`test_guard_dispatch_contract.py`, `test_guard_broad_grep.py`) log real `block` actions directly into shared audit logs (`dispatch_audit.jsonl`, `guard_scan_audit.jsonl`). Over 70% of reported violations were synthetic test assertions.
2. **Local Naive vs UTC Timezone Desync**: Logs generated with `datetime.now().isoformat()` emit naive strings in local time (UTC+7, e.g. `10:49`). Watchdogs evaluating in UTC that parse naive timestamps using `.replace(tzinfo=timezone.utc)` interpret 10:49 as UTC (17:49 VN), shifting the 6-hour rolling window by 7 hours and pulling in historical incidents from 13 hours prior.
3. **Three-Way Script Deployment Skew**: Scripts modified in developer worktrees (`D:/Taadaa/tools/` or `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`) fail to reflect in production cron execution because Hermes cron runs standalone scripts from `%LOCALAPPDATA%\hermes\scripts\`.

---

## 2. Root Causes & Technical Breakdown

### A. The Incomplete Test Signature Anti-Pattern
Watchdogs previously attempted to filter test artifacts using a naive pattern:
```python
# ANTI-PATTERN: Fails to catch 90% of pytest assertions
def is_test_log_line(line: str) -> bool:
    return bool(re.search(r"pytest", line, re.IGNORECASE) and re.search(
        r"(?:workdir|file|target)\s*[=:]\s*['\"]?[^,\s]*pytest|target\.py",
        line, re.IGNORECASE,
    ))
```
When pytest runs contract tests, the logged goal is the test string itself:
- `Review then apply constant change` (86 occurrences)
- `Review "quoted" & $HOME whoami change 'single' then apply` (13 occurrences)
- `grep -rn foo D:/Taadaa` (16 occurrences)
- `grep.exe -rn count_active_locks D:/Taadaa/Hermes` (8 occurrences)
- `python3.exe -c "import os; os.walk('D:/Taadaa')"` (8 occurrences)
None of these lines contain `pytest` or `target.py`, causing the watchdog to treat unit test executions as real operational failures.

### B. Naive Timezone Window Distortion
- `dispatch_audit.jsonl` record: `{"timestamp": "2026-10-26T10:49:28.503866", "action": "block"}` (Recorded at 10:49 AM VN = 03:49 UTC).
- Watchdog execution at 15:30 VN (08:30 UTC): 6-hour cutoff is 02:30 UTC.
- When parsed with naive `.replace(tzinfo=timezone.utc)`: 10:49 is parsed as 10:49 UTC (which is in the future relative to 08:30 UTC, or shifts relative windows by +7h).
- Conversely, entries from 18:00 VN yesterday (11:00 UTC yesterday) were interpreted as 18:00 UTC, falsely falling inside cutoff windows!

### C. Standalone Script Lifecycle vs Gateway Memory State
When users ask: *"Xong hết chưa, có cần restart Gateway không?"*:
- **`no_agent: true` cronjobs**: Execute standalone Python processes per tick via Windows `subprocess`. They read `%LOCALAPPDATA%\hermes\scripts\<script>.py` fresh from disk on every invocation. **ZERO gateway restart needed**.
- **In-Memory Gateway Restart Only Required For**: Changes to Hermes core engine modules residing in RAM (`conversation_loop.py`, `coding_context.py`, `slash_commands.py`).

---

## 3. The Canonical Solution Architecture

### 1. Comprehensive Test Mock Signature Sanitization
Maintain an explicit, fast-matching tuple of known test mock payload signatures:
```python
TEST_MOCK_SIGNATURES = (
    "pytest", "tmp_path", "target.py", "pytest-of-Kibe",
    "Review then apply constant change", "Review \"quoted\"", "Review 'quoted'", "backtick",
    "Batch constant changes", "Create a helper", "Investigate D:/Taadaa/tools/x.py",
    "count_active_locks", "grep -R lock", "--recursive token", "rg count_active",
    "rg.exe pattern", "rg pattern", "grep -rn foo", "audit_test",
    "os.walk('D:/Taadaa')", 'os.walk("D:/Taadaa")', "list(Path('D:/').rglob",
    'list(Path("D:/").rglob', "glob.glob('D:/**/*'", 'glob.glob("D:/**/*',
    "find . -name", "Get-ChildItem -Recurse",
    "script.py", "script.ps1", "bad.py", "bad_sub.py", "lookalike_flags", "other_alias_flags",
    "does_not_exist", "farm_action.py", "farm_burst.py", "fake_lock.py", "fake_fn.py",
    "fake_module.py", "empty_body.py", "nonexistent_runner",
)

def is_test_log_line(line: str) -> bool:
    line_lower = line.lower()
    return any(sig.lower() in line_lower for sig in TEST_MOCK_SIGNATURES)
```

### 2. Designated Naive File Local-to-UTC Normalization
```python
LOCAL_NAIVE_LOGS = {"dispatch_audit.jsonl", "console_block_audit.jsonl"}

def parse_line_timestamp(line: str, path_name: str = "") -> datetime | None:
    ...
    if dt.tzinfo is None:
        dt = (dt.astimezone().astimezone(timezone.utc)
              if path_name in LOCAL_NAIVE_LOGS
              else dt.replace(tzinfo=timezone.utc))
    return dt
```

### 3. Three-Way Sync Enforcement (`cron_sync_watchdog.py`)
Always verify hash parity across all three environments:
1. Canonical Repo: `D:/Taadaa/tools/<script>.py`
2. Git Deploy: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py`
3. Hermes Cron Runtime: `%LOCALAPPDATA%\hermes\scripts\<script>.py`
Execute `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py --force` to flush changes to runtime immediately without gateway restarts.
