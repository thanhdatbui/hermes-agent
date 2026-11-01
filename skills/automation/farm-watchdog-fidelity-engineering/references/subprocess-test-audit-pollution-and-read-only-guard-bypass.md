# Subprocess Test Audit Pollution and Read-Only Guard Discrimination

## 1. Operational Symptoms
During 6-hour farm gate compliance audits, `gate_compliance_watchdog.py` periodically triggers high false-positive alarms:
- **G8 Cronjob Window Guard**: Dozens of sudden violations (`CRON_AGENT_POLICY`, `FARM_CONTRACT_INVALID`, `WORKER_CAP_EXCEEDED`, `NO_AGENT_REQUIRED`).
- **G9 Farm & GPM Proxy Guard**: False violations on read-only inspection commands (`android_proxy_domain_block`).

---

## 2. Root Cause 1: Subprocess Test Telemetry Leakage (The Monkeypatch Trap)

### Problem Mechanism
When testing security hooks (such as `hooks/guard_cronjob_safety.py`), test suites often invoke the hook as an isolated subprocess:
```python
# ANTI-PATTERN: monkeypatch does NOT propagate across subprocess boundary
def test_cron_contract(monkeypatch, tmp_path):
    monkeypatch.setattr(guard_module, "AUDIT_LOG", tmp_path / "audit.jsonl")
    proc = subprocess.run([sys.executable, str(HOOK_PATH)], input=json.dumps(payload))
```
1. In-process `monkeypatch` modifies module attributes only within the parent pytest runner memory space.
2. The spawned child process re-imports the hook fresh and uses its hardcoded production default `AUDIT_LOG = D:/Taadaa/runtime/audit_logs/console_block_audit.jsonl`.
3. Every assert testing invalid inputs (`max_workers=100`, `lock_ttl_s=-1`, `no_agent=False`, `attacker_injected_key`) writes a real `decision: block` entry directly into production logs.
4. Because these payloads contain pure semantic values without file paths, temporary directories, or the word `"pytest"`, watchdog sanitizers (`is_test_log_line()`) fail to recognize them as test mocks.

### Invariant Fix
1. **Environment-Variable Audit Redirection**: Hooks must read `AUDIT_LOG = Path(os.environ.get("HERMES_AUDIT_LOG_PATH", DEFAULT_AUDIT_LOG))`. Subprocess tests must pass `env={**os.environ, "HERMES_AUDIT_LOG_PATH": str(tmp_path / "audit.jsonl")}`.
2. **Watchdog Mock Signature Parity**: Add synthetic contract signatures to `TEST_MOCK_SIGNATURES`:
   `("attacker_injected_key", "farm_contract max_workers", "lock_ttl_s=", "touches_device bắt buộc", "farm_burst.py", "farm_mult_burst.py")`.

---

## 3. Root Cause 2: Inspection vs Execution Command Discrimination

### Problem Mechanism
A developer or agent investigating proxy configuration executed:
```bash
grep -rn "settings put global http_proxy" "D:/Taadaa/tiktok-luot nuoi acc/python_runner"
```
`guard_proxy.py` matched the substring `"settings put global http_proxy"` in the command line and evaluated it as an illegal proxy modification, logging `android_proxy_domain_block`.

### Invariant Fix
Security guard hooks intercepting terminal commands MUST discriminate between:
1. **Inspection/Search commands** (`grep`, `rg`, `git grep`, `cat`, read-only queries): Must NEVER be evaluated for execution-level syntax/mutation violations.
2. **Execution/Mutation commands** (`adb shell settings put ...`, direct python invocation mutating state): Must be strictly guarded.

---

## 4. Root Cause 3: Agent Panic Disk-Walking Anti-Pattern
When tasked with investigating missing reports or cron status, agents frequently panic and resort to broad scans:
- `python -c "import os; for ... os.walk('D:/Taadaa/...')"` (`GUARD_PYTHON_WALKER`)
- `find /d/Taadaa -maxdepth 3 ...` (`GUARD_FIND_SCAN`)
- `grep -rn ...` (`GUARD_RECURSIVE_GREP`)
- Direct un-locked ADB commands (`GUARD_DEVICE_LOCK_REQUIRED`) or manual UI clicks (`GUARD_MANUAL_ADB_TAP`).

### Guidance
- When investigating farm state or missing reports, Coordinator/Agent must look directly at known, single-point audit files (`runtime/audit_logs/`, `logs/`, or `python D:/Taadaa/tools/inspect_machine.py <N>`), never scan or walk directory trees.
