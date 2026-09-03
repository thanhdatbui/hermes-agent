# Device Workflow Regression Recipe

Use this recipe for consumer-repository state-machine fixes where device readiness, manual escalation, reporting, and lock cleanup interact.

## Required behavior

- `run_post` reports `MANUAL_REVIEW` from `machine.current_state`.
- `CONNECT_DEVICE` treats `readiness.unlock_state == "locked_or_secure"` as a hard safety gate.
- The gate records a structured error/checkpoint, sets a manual-review signal, and returns before adapter/media initialization; no TikTok launch or account switcher is reached.
- Execution releases acquired device/workbook leases in an outer `finally`, including exception paths. Release is idempotent; do not delete unrelated stale locks.
- Tests use fake ADB/readiness/lease objects only. Never use live devices, uploads, passwords, or credential bypasses.

## Focused assertions

```python
assert not machine._handle_connect_device()
assert machine.context.is_device_locked
assert "DEVICE_LOCKED_OR_SECURE" in machine.context.error
machine._transition(False)
assert machine.current_state is WorkflowState.MANUAL_REVIEW
assert machine.context.adapter is None
```

For cleanup, inject a lease with a `released` flag, force the execution body to raise, and assert the flag is true after `machine.execute(...)` propagates the exception.

## Fresh ad-hoc verification

When the workspace is marked unverified or no canonical command is detected, generate a script with:

```python
fd, path = tempfile.mkstemp(
    prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir(), text=True
)
```

Run it with the repository import path configured, print a distinctive pass marker, and delete it in `finally`. Report this as **ad-hoc verification**, separately from pytest/full-suite/compile/import evidence.
