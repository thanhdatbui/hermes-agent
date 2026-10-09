# Batch Aggregation Mode — alerts.py + batch_aggregator.py + PS1 hook

## Env-flag architecture

| Env var | Value | Behaviour |
|---|---|---|
| `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT` | unset / `0` / `false` / `no` / `off` | **Suppressed** — `send_farm_machine_alert` returns `dict{"suppressed": True, "status": "suppressed_for_batch", "machine": N, "chat_id": "..."}` instead of `bool`. No Telegram send; per-machine alerts are deferred to batch aggregator. |
| `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT` | `1` / `true` / `yes` / `on` | **Live** — alert fires immediately like before. |

Helper function: `alerts._should_suppress_immediate_machine_alert()` — returns `True` when suppressed.

## Suppression dict shape

```python
{
    "status": "suppressed_for_batch",
    "machine": <int>,
    "chat_id": "<str>",
    "suppressed": True,
}
```

Code downstream that checks `if result is True` or `if not result` must be updated to handle dict.

---

## ⚠️ PITFALL: Pre-existing tests break after adding suppression

**Problem:** Tests that set `FORCE_TEST_ALERT_DISPATCH=1` + `delenv("PYTEST_CURRENT_TEST")` to enter the
"real" code path will now hit the suppression check **before** `_load_bot_token()` is called.
The function returns the suppression dict, not `True`/`False`, so assertions like `assert result is True`
or `assert result is False` fail.

**Root cause sequence:**
1. `_is_test_environment()` → `False` (because `PYTEST_CURRENT_TEST` was deleted and `FORCE_TEST_ALERT_DISPATCH=1`)
2. `_should_suppress_immediate_machine_alert()` → `True` (env var not set) → returns dict immediately

**Fix: add this monkeypatch to EVERY pre-existing test that uses FORCE_TEST_ALERT_DISPATCH:**
```python
monkeypatch.setenv("AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT", "1")
```
Place it immediately after the `FORCE_TEST_ALERT_DISPATCH` line.

**New suppression-path tests** must NOT set this var (they are testing the suppress path itself).

---

## load_results_from_run_dir — two artifact directory layouts

`batch_aggregator.load_results_from_run_dir(run_dir)` supports:

### Layout 1 (preferred): `run_dir/machines/<serial>/run_manifest.json`
```
run_dir/
  machines/
    m1/
      run_manifest.json   {"serial": "m1", "status": "completed"}
    m2/
      run_manifest.json   {"serial": "m2", "status": "failed", "error_type": "...", ...}
```

### Layout 2 (fallback): `run_dir/<any_subdir>/run_manifest.json`
```
run_dir/
  job_abc/
    run_manifest.json   {"serial": "m99", "status": "success"}
```

Layout 1 is tried first. Layout 2 is used only when no `machines/` child subdirs have manifests.

`parse_results_from_file(path)` auto-delegates to `load_results_from_run_dir(path)` when `path.is_dir()`.

### run_manifest.json schema
```json
{
  "serial":        "m1",
  "status":        "completed|success|ok|failed|...",
  "error_type":    "TimeoutError",
  "error_message": "timed out waiting for screen",
  "snapshot_png":  "/path/to/screen.png",
  "snapshot_xml":  "/path/to/ui.xml"
}
```
`succeeded = status in ("completed", "success", "ok")`

---

## PS1 hook in run-feed-session.ps1

After `& $Python @arguments`, the hook calls batch aggregator:

```powershell
& $Python @arguments

if ($runDir -and (Test-Path $runDir)) {
    try {
        python -m automation_core.batch_aggregator "$runDir" --telegram
    } catch {
        Write-Warning "batch_aggregator hook error: $_"
    }
}

exit $LASTEXITCODE
```

**Requirement:** `$runDir` must be set in the PS1 before the runner call (pointing at the artifact
root for the current run). If unset or path does not exist, the hook silently skips (safe).

---

## alerts.py changes summary (2026-09-08)

- Added `import logging` + `log = logging.getLogger(__name__)`
- Added `_should_suppress_immediate_machine_alert() -> bool`
- `send_farm_machine_alert`: returns suppression dict when env var absent/falsy, logs at INFO level
- All prior bool-returning behaviour preserved when `AUTOMATION_CORE_IMMEDIATE_MACHINE_ALERT=1`

## batch_aggregator.py changes summary (2026-09-08)

- Added `load_results_from_run_dir(run_dir)` — Layout 1 + 2 directory scanning
- `parse_results_from_file()` — added `if p.is_dir(): return load_results_from_run_dir(p)` branch
