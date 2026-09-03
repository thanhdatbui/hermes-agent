# Batch Lock Release Pattern — 2026-08-12

## Context
Released all FAILED/MANUAL_REVIEW device locks for Tik2 batch `tik2_live_20260812_171328` (65 machines) using the guarded automation-core API instead of the manual CLI script. This is the programmatic equivalent of `release-device-lock.py` but for batch operations.

## Allowlist Derivation
From `safe-report-summary.csv`:
- Target = rows where `launch=STARTED` AND `status != SUCCESS`
- Explicitly exclude: SUCCESS machines, NOT_LAUNCHED machines, machines with no lock file

## Preflight Verification (Mandatory)
```python
# 1. No tiktok_workflow processes alive
import psutil
assert not any('tiktok_workflow' in ' '.join(p.cmdline()) for p in psutil.process_iter(['cmdline']))

# 2. For each target machine:
#    - machine_<m>.lock.json exists
#    - owner.host == current host
#    - owner.pid is dead (psutil.NoSuchProcess)
#    - owner.project == 'tiktok-upload'
#    - 'Tik2.xlsx' in owner.command AND 'Tiktok-video' in owner.command
#    - owner.status in {'handoff', 'blocked', 'failed_locked'} (NOT 'running', 'queued', 'recovery')
#    - owner.owner_active == False
```

## Core API Pattern (Guarded, No Raw Deletion)
```python
from automation_core.device_lock import (
    acquire_device_lock, DeviceLockLease,
    FULL_SCOPE_TAKEOVER, DEFAULT_LOCK_ROOT
)

reason = 'operator explicit 2026-08-12: release failed Tik2 batch 20260812_171328 locks'

# Phase 1: Machine locks
for machine in target_machines:
    lease = acquire_device_lock(
        machine=machine,
        project='tiktok-upload',
        lock_root=DEFAULT_LOCK_ROOT,
        status='handoff',  # current status of retained locks
        allow_takeover=True,
        takeover_scope=FULL_SCOPE_TAKEOVER,
        takeover_authorized=True,
        takeover_reason=reason,
    )
    # Verify batch match before release
    owner = _safe_read_json(lease.lock_paths[0])
    assert 'Tik2.xlsx' in str(owner.get('command','')) and 'Tiktok-video' in str(owner.get('command',''))
    
    audit = lease.release_with_audit(reason=reason)
    # audit.released_paths contains deleted file paths

# Phase 2: Serial locks (same pattern, acquire by serial)
for machine in target_machines:
    serial = find_serial_for_machine(machine)  # from remaining serial_*.lock.json
    lease = acquire_device_lock(
        serial=serial,
        project='tiktok-upload',
        lock_root=DEFAULT_LOCK_ROOT,
        status='handoff',
        allow_takeover=True,
        takeover_scope=FULL_SCOPE_TAKEOVER,
        takeover_authorized=True,
        takeover_reason=reason,
    )
    audit = lease.release_with_audit(reason=reason)
```

## Key Contract Requirements
- `takeover_authorized=True` — explicit user authorization (fail-closed without it)
- `takeover_scope=FULL_SCOPE_TAKEOVER` — cross-project takeover (SAME_PROJECT_RECOVERY would require project match)
- `takeover_reason` — non-empty, audited in `DeviceLockOpenAudit` / `DeviceLockReleaseAudit`
- `status='handoff'` — matches the retained lock's current status; acquire will claim it
- `release_with_audit()` — returns `DeviceLockReleaseAudit` with `released_paths` (proof of mutation)

## Verification Post-Mutation
1. All target `machine_*.lock.json` and `serial_*.lock.json` gone
2. Non-target locks untouched (other consumers/batches)
3. No `tiktok_workflow` processes spawned
4. Audit artifact written with: targets, results, skipped, verification, method

## Audit Artifact Schema
```json
{
  "timestamp": "ISO8601",
  "batch": "tik2_live_20260812_171328",
  "reason": "...",
  "allowlist_source": "safe-report-summary.csv rows with launch=STARTED and status!=SUCCESS",
  "targets": { "total_target_machines": 65, "machines": [...], "excluded": {...} },
  "results": { "machine_locks_released": 65, "serial_locks_released": 64, "skipped": {...}, "failed": 0 },
  "verification": { "non_target_locks_unaffected": [...], "target_machine_locks_removed": true, ... },
  "method": "guarded automation-core acquire_device_lock with FULL_SCOPE_TAKEOVER, takeover_authorized=True, followed by lease.release_with_audit()",
  "audit_files": [...]
}
```

## Pitfalls Avoided
- ❌ Raw `os.unlink()` / `Path.unlink()` — bypasses guard protocol, no audit, can corrupt alias consistency
- ❌ `release-device-lock.py` in a loop — CLI overhead, no batch verification, no consolidated audit
- ❌ Releasing locks with `owner_active=True` — would indicate live worker, must refuse
- ❌ Releasing locks from other projects/batches — must verify `project` and `command` fields
- ❌ Skipping preflight process check — stale PID may appear alive on Windows (`os.kill(pid,0)` unreliable; use `tasklist` or `psutil`)

## When to Use This Pattern
- Batch release of retained locks after a failed/aborted multi-machine run
- Operator-explicit cleanup with full audit trail
- Cross-consumer lock recovery (FULL_SCOPE_TAKEOVER)
- When CLI script is too slow or lacks batch verification