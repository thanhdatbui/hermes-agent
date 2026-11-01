# Subprocess Test Audit Isolation & Watchdog Sanitization

## 1. Context & Operational Symptoms
When running 6-hour or rolling compliance audits (`gate_compliance_watchdog.py`), gates frequently trigger severe false-positive failures (e.g. `G8 Cronjob Window Guard: FAIL (44 violations)`, `G3 Worker Dispatch Gate: FAIL`).
The top reported violations often mimic exact test assertions:
- `[Cronjob Window] CRON_AGENT_POLICY: 12`
- `[Cronjob Window] FARM_CONTRACT_INVALID: 11`
- `[Cronjob Window] WORKER_CAP_EXCEEDED: 7`
- `[Cronjob Window] NO_AGENT_REQUIRED: 6`
- `[Cronjob Window] CONSOLE_WINDOW: 6` (`ssh admin-farm 'powershell -Command Get-Process'`)

---

## 2. Root Cause: In-Process Monkeypatch Bypass in Subprocesses

### A. The Subprocess Monkeypatch Trap
Unit tests (such as `test_guard_cronjob_safety.py`) frequently invoke guard hooks as separate CLI processes:
```python
# ANTI-PATTERN: monkeypatching guard_module has ZERO effect on subprocesses
@pytest.fixture
def audit_log(tmp_path, guard_module, monkeypatch):
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(guard_module, "AUDIT_LOG", audit)
    return audit

def run_hook(payload: dict) -> dict:
    proc = subprocess.run([sys.executable, str(HOOK_PATH)], input=json.dumps(payload), ...)
```
Because `subprocess.run` starts a completely fresh Python interpreter, it re-evaluates the hook script at top-level. If the hook hardcodes:
```python
AUDIT_LOG = Path("D:/Taadaa/runtime/audit_logs/console_block_audit.jsonl")
```
every test assertion (`max_workers=100`, `no_agent=false`, invalid ttl) is written straight into the **production** audit log file.

### B. Gate 5 Repository Write Violation
Attempting to redirect the subprocess audit file to `tests/audit.jsonl` within the test directory causes Unified Patch Pipeline Gate 5 to fail with:
`Gate 5 sau test thất bại — tạo/sửa file NGOÀI scope: tests/audit.jsonl`.
Tests must strictly write temporary artifacts inside the OS temporary directory (`tempfile.gettempdir()`).

---

## 3. The 3-Tier Mitigation Architecture

### Tier 1: Environment-Variable-Driven Audit Path in Hook
In `guard_cronjob_safety.py`:
```python
AUDIT_LOG = Path(os.environ.get("AUDIT_LOG_PATH", "D:/Taadaa/runtime/audit_logs/console_block_audit.jsonl"))
```

### Tier 2: Subprocess Environment Injection in Unit Tests
In `tests/test_guard_cronjob_safety.py`:
```python
def run_hook(payload: dict) -> dict:
    import tempfile
    env = os.environ.copy()
    env["AUDIT_LOG_PATH"] = str(Path(tempfile.gettempdir()) / "cron_audit_test.jsonl")
    proc = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=25,
        env=env,
    )
    return json.loads(proc.stdout) if proc.stdout.strip() else {"action": "allow"}
```

### Tier 3: Watchdog Test Mock Signature Sanitization
In `gate_compliance_watchdog.py`, ensure `TEST_MOCK_SIGNATURES` catches historical test artifacts that were previously logged:
```python
TEST_MOCK_SIGNATURES = (
    ...,
    "cron_agent_policy", "farm_contract", "fake_module",
    "attacker_injected_key", "farm_burst", "test_ssh_powershell",
    "unsafe_ssh.py", "bad_runner.py", "powershell -command get-process",
)
```

---

## 4. Verification Invariants
1. Running `pytest tests/test_guard_cronjob_safety.py` must produce **0 additional bytes** in `D:/Taadaa/runtime/audit_logs/console_block_audit.jsonl`.
2. Running `python gate_compliance_watchdog.py --hours 6` must report G8 as clean with 0 synthetic violations.
3. Subprocess audit test files must never be committed or written into the git repository tree.
