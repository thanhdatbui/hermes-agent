# Upload Hook Test Conventions & Allow-Hook Flag

## Context
In `flows/multi_machine_feed_session.py`, `_run_upload_hook` gates execution using:
```python
allow_hook = bool(ctx.config.get("_allow_upload_hook"))
if session_index != 2 and not allow_hook:
    payload = {
        "machine": account.machine,
        "row": account.account_row_index,
        "status": "skipped",
        "reason": "not-final-session" if session_index else "missing-session-identity",
        "session_index": session_index or None,
    }
    _write_upload_result(child_ctx, payload)
    return payload
```

## Pitfall in Tests
When tests initialize dummy context with `session_index=3` (or any value other than `2`):
- `_run_upload_hook` will immediately skip with `reason="not-final-session"` unless `_allow_upload_hook=True` is provided.
- Ensure `_make_dummy_context` sets `_allow_upload_hook`:
```python
def _make_dummy_context(
    tmp_path: Path,
    machine: int = 5,
    session_index: int = 3,
    allow_upload_hook: bool | None = None,
) -> tuple[DeviceContext, DeviceContext, MachineAccount]:
    if allow_upload_hook is None:
        allow_upload_hook = (session_index != 1)
    # ...
    # Set in both ctx.config and child_ctx.config:
    ctx.config["_allow_upload_hook"] = allow_upload_hook
    child_ctx.config["_allow_upload_hook"] = allow_upload_hook
```
- For tests specifically asserting `gate1` (non-final session skipping), pass `session_index=1` and `_allow_upload_hook=False`.
