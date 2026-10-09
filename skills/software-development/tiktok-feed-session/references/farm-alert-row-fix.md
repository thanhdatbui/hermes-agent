# Farm Alert: Row Hardcode Fix (2026-09-08)

## Problem

`_send_farm_machine_alert_once` in `multi_machine_feed_session.py` had the canary
command hardcoded to `-Row 1`, regardless of the actual workbook row the machine
was running. Farm Alerts also showed no Row field in the message body.

## Root Cause

Three coupled hardcodes:

1. `_SCRIPT_METADATA["feed"]["default_canary"]` lambda took only `m` — no `row` param.
2. `_resolve_script_meta()` never passed `row` to the lambda.
3. `_send_farm_machine_alert_once()` never received `row` from its callers.

## Fix Applied

### `automation-core/src/automation_core/alerts.py`

**Lambda signature** — added `row=1` default:
```python
"default_canary": lambda m, row=1: f'... -Machines {m} -Row {row} -RecoveryTestSwipes 2 ...'
```

**`_resolve_script_meta`** — added `row: int | None = None` param; uses
`inspect.signature` to detect lambdas with ≥ 2 params and passes `row` when set:
```python
def _resolve_script_meta(script_name, machine=None, row=None):
    ...
    if len(sig.parameters) >= 2 and row is not None:
        canary = canary_fn(m_val, row)
    else:
        canary = canary_fn(m_val)
```

**`send_farm_machine_alert`** — added `row: int | None = None` param; passes it
to `_resolve_script_meta`; shows `| Row: {row}` in the Telegram message line:
```python
row_display = f" | Row: {row}" if row is not None else ""
f"• Máy: {machine}{row_display} | Serial: ... | Nick: ..."
```

### `tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py`

**`_send_farm_machine_alert_once`** — added `row: int | None = None` param;
resolves `_row = row if row is not None else 1`; passes `row=_row` and correct
`canary_cmd` with `-Row {_row}`:
```python
canary_cmd=f'... -Machines {machine} -Row {_row} -RecoveryTestSwipes 2 ...'
```

## Remaining Step (not completed — tool-call limit hit)

Both **call sites** of `_send_farm_machine_alert_once` (~line 5513 and ~5597 in
`multi_machine_feed_session.py`) still need `row=child.account_row_index` added.
`MachineFeedSessionResult` has the field; the callers just need to pass it:

```python
_send_farm_machine_alert_once(
    ctx,
    machine=child.machine,
    serial=child.serial,
    account=child.expected_username,
    error_reason=child.stop_reason or child.final_status,
    adb_path=resolved_adb or fallback_adb,
    row=child.account_row_index,   # ← ADD THIS at both call sites
)
```

## Pattern for Future Canary Commands

When `_SCRIPT_METADATA` lambdas need more than just `machine`, always:
1. Add the extra param with a safe default to the lambda.
2. Add the matching param to `_resolve_script_meta` and `send_farm_machine_alert`.
3. Use `inspect.signature` in `_resolve_script_meta` to avoid breaking callers
   that pass only `m`.
4. Pass the real value at every `_send_farm_machine_alert_once` call site using
   `object.account_row_index` (always live on `MachineFeedSessionResult`).
