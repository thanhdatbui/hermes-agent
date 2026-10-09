# Pinned User Locks, Hard Done Gates & Anti-Confabulation Protocol

Date: 2026-09-19
Scope: `automation-core` (`device_lock.py`), `tools/done_gate.py`, and Reaper architecture.

---

## 1. Pinned User Lock Architecture (`user_authorized=True`)

### Problem Statement:
Advisory/trust-based locking fails when ad-hoc test scripts or batch runners bypass `acquire_device_lock()`. Automated cronjobs (feed runner, avatar watchdog) scan device locks, find no lock record, and preempt active foreground apps (e.g. Chrome ChatGPT link flow interrupted by TikTok launch).

### Design Solution (Sol Auditor + Claude SRE Reconciled):
1. **Lock Schema Fields:**
   - `"user_authorized": True`
   - `"pinned": True`
   - `"ttl_seconds": 3600` (1 hour hard TTL per user requirement)
   - `"last_heartbeat": "<ISO-timestamp>"`
2. **Preemption Immunity:**
   - Background automated jobs (`user_authorized=False`) inspecting a device holding `pinned=True` MUST raise `DeviceLockNeedsUserDecision` and immediately abort/skip. They are hard-blocked from taking over the device.
3. **Heartbeat & Reaper TTL 1h:**
   - To prevent overnight deadlock if an agent or user session crashes, `reap-dead-owner-locks.py` respects:
     - Dead owner PID (`owner_alive is False`): Reaped immediately to quarantine.
     - Active/Unknown owner with age >= 3600s (1 hour): Reaped to quarantine with `pinned_timeout_1h`.
     - Active owner with age < 3600s: Retained and protected from all preemption.
4. **DeviceContext Wrapper:**
   ```python
   with DeviceContext(serial="...", machine=..., project="...", user_authorized=True) as lease:
       # Exclusive uninterrupted device operations
       ...
   ```

---

## 2. Hard Done Gate (`D:/Taadaa/tools/done_gate.py`)

### Problem Statement:
LLM drift toward early declaration of "DONE" upon unit test pass and git commit, skipping mandatory physical device verification (Canary).

### Mechanism:
- CLI command: `python D:/Taadaa/tools/done_gate.py --task-type automation --canary-file <path>`
- Exit code 1 (`GATE-FAIL`): If task is automation and farm has idle devices but no fresh (<2h) Canary evidence.
- Exit code 0 (`GATE-PASS`): Valid Canary evidence provided OR fleet 100% busy (`.canary_pending` flag) OR task is general non-automation.

---

## 3. Anti-Confabulation Protocol

### Rule:
Zero tolerance for defensive rationalization ("em tưởng", "thừa 1 nhịp hỏi", "lần sau sẽ cẩn thận").
When challenged on a failure, the ONLY accepted response format is:
```text
[FAULT-CONFIRMED]: <Specific Failure Name>
- Evidence: <Log citation or history snippet proving the failure>
- Root Cause: <Technical cause, no psychological framing>
- Structural Fix: <File, hook, or script created to prevent recurrence>
- Verification: <Concrete test/check command executed>
```
