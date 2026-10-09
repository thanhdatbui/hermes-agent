# Focused Gmail health-check and DIE-cleanup testing

## Scope

For a workbook-backed Gmail health-check module that cleans confirmed DIE accounts from S7, keep pytest offline. Do not invoke Playwright, network, ADB, OneDrive workbooks, or the live farm runner.

## Recommended seams

Split the workflow into injectable boundaries:

- candidate loading: normalized Gmail, soak-age/status gate, explicit force override;
- workbook update: temporary save followed by `os.replace`, with rows preserved;
- proxy/machine mapping and ADB-online discovery;
- device-lock acquisition;
- on-device account-presence check;
- removal operation;
- append-only DIE log.

## Minimum regression matrix

1. Eligibility accepts valid Gmail and the soak threshold, rejects recent/already-processed rows, and honors `force`.
2. Atomic status update changes only matching rows and asserts the temporary path plus replace boundary.
3. Offline devices, missing mappings, and lock contention skip without calling removal.
4. Successful cleanup removes only a present DIE account and writes a durable machine/serial/timestamp log.

## Legacy tool-tree import pattern

When the tool directory is not a Python package, load the production module by absolute path:

```python
spec = importlib.util.spec_from_file_location("target", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
```

Registering in `sys.modules` before execution avoids inconsistent behavior for module metadata and nested imports. Use in-memory workbook doubles and monkeypatch external seams. After any final source or test edit, rerun the exact focused pytest target; earlier results are stale.
